"""Send and remove books on the CrossPoint device."""

from __future__ import annotations

import asyncio
import logging
import posixpath
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util import dt as dt_util

from .api.errors import CrossPointError, CrossPointResponseError
from .const import (
    CONF_BOOKS_DIR,
    CONF_DEVICE_BOOKS_DIR,
    CONF_LIBRARY_PATH,
    DEFAULT_DEVICE_BOOKS_DIR,
    DOMAIN,
    EVENT_UPLOAD_PROGRESS,
    KIND_BOOK,
)
from .store import Transfer, TransferStore, sha256_file

if TYPE_CHECKING:
    from . import CrossPointConfigEntry
    from .coordinator import CrossPointDeviceCoordinator

_LOGGER = logging.getLogger(__name__)

# Fire at most one progress event per this many bytes.
_PROGRESS_STEP = 256 * 1024


@dataclass(frozen=True, slots=True)
class _LocalFile:
    path: Path
    data: bytes
    sha256: str


def _error(key: str, **placeholders: str) -> HomeAssistantError:
    return HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key=key,
        translation_placeholders=placeholders or None,
    )


def _validation_error(key: str, **placeholders: str) -> ServiceValidationError:
    return ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key=key,
        translation_placeholders=placeholders or None,
    )


class BookManager:
    """Book operations for one config entry."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: CrossPointConfigEntry,
        coordinator: CrossPointDeviceCoordinator,
        store: TransferStore,
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._coordinator = coordinator
        self._client = coordinator.client
        self._store = store
        self._root = Path(entry.data[CONF_LIBRARY_PATH]) / entry.data[CONF_BOOKS_DIR]
        # Serialize whole operations so the store stays consistent.
        self._lock = asyncio.Lock()

    @property
    def device_dir(self) -> str:
        """Destination folder for books on the SD card."""
        return self._entry.options.get(CONF_DEVICE_BOOKS_DIR, DEFAULT_DEVICE_BOOKS_DIR)

    def normalize(self, file: str) -> str:
        """Return a safe path relative to the books folder, or raise."""
        rel = PurePosixPath(file.strip().lstrip("/"))
        if not rel.parts or ".." in rel.parts:
            raise _validation_error("invalid_file", file=file)
        return rel.as_posix()

    def _read(self, rel: str) -> _LocalFile:
        """Read a library book and hash it (blocking; run in the executor)."""
        root = self._root.resolve()
        path = (root / rel).resolve()
        if not path.is_relative_to(root):
            raise _validation_error("invalid_file", file=rel)
        if not path.is_file():
            raise _validation_error("file_not_found", file=rel)
        return _LocalFile(path=path, data=path.read_bytes(), sha256=sha256_file(path))

    async def async_send(self, file: str, *, overwrite: bool = False) -> Transfer:
        """Upload a library book to the device and track it."""
        rel = self.normalize(file)
        async with self._lock:
            await self._coordinator.async_ensure_online()
            local = await self._hass.async_add_executor_job(self._read, rel)
            tracked = self._store.get(KIND_BOOK, rel)
            filename = local.path.name
            device_path = posixpath.join(self.device_dir, filename)
            # A tracked book is ours to replace (e.g. modified after sending).
            replace = overwrite or (
                tracked is not None and tracked.device_path == device_path
            )

            try:
                await self._client.ensure_dir(self.device_dir)
                device_path = await self._client.upload(
                    local.data,
                    self.device_dir,
                    filename,
                    overwrite=replace,
                    progress=self._progress_reporter(rel),
                )
            except CrossPointResponseError as err:
                if "exist" in str(err).lower():
                    raise _validation_error(
                        "file_exists_on_device", file=filename
                    ) from err
                raise _error("device_error", error=str(err)) from err
            except CrossPointError as err:
                self._coordinator.async_mark_connection_lost(err)
                raise _error("connection_lost", error=str(err)) from err

            if tracked and tracked.device_path != device_path:
                _LOGGER.warning(
                    "%s was previously sent to %s; it is now at %s",
                    rel,
                    tracked.device_path,
                    device_path,
                )
            return await self._store.async_record(
                kind=KIND_BOOK,
                file=rel,
                sha256=local.sha256,
                size=len(local.data),
                sent_at=dt_util.utcnow(),
                device_path=device_path,
            )

    async def async_remove(self, file: str, *, forget_missing: bool = False) -> None:
        """Delete a tracked book from the device, then stop tracking it."""
        rel = self.normalize(file)
        async with self._lock:
            tracked = self._store.get(KIND_BOOK, rel)
            if tracked is None:
                raise _validation_error("not_tracked", file=rel)
            await self._coordinator.async_ensure_online()
            try:
                await self._client.delete(tracked.device_path)
            except CrossPointResponseError as err:
                if not await self._async_missing_on_device(tracked.device_path):
                    raise _error("device_error", error=str(err)) from err
                if not forget_missing:
                    raise _validation_error(
                        "not_on_device", file=tracked.device_path
                    ) from err
            except CrossPointError as err:
                self._coordinator.async_mark_connection_lost(err)
                raise _error("connection_lost", error=str(err)) from err
            await self._store.async_forget(KIND_BOOK, rel)

    async def _async_missing_on_device(self, device_path: str) -> bool:
        """Return True if the device listing confirms the file is gone."""
        parent, name = posixpath.split(device_path)
        try:
            files = await self._client.list_files(parent or "/")
        except CrossPointResponseError:
            return True  # the parent folder itself is gone
        return all(f.name != name for f in files)

    def _progress_reporter(self, rel: str):
        last = -_PROGRESS_STEP

        def report(received: int, total: int) -> None:
            nonlocal last
            if received - last < _PROGRESS_STEP and received < total:
                return
            last = received
            self._hass.bus.async_fire(
                EVENT_UPLOAD_PROGRESS,
                {
                    "entry_id": self._entry.entry_id,
                    "kind": KIND_BOOK,
                    "file": rel,
                    "received": received,
                    "total": total,
                },
            )

        return report
