"""Send files to the CrossPoint device and remove them again."""

from __future__ import annotations

import asyncio
import logging
import posixpath
from collections.abc import Callable
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
class LocalFile:
    """A library file read into memory."""

    path: Path
    data: bytes
    sha256: str


def translated_error(key: str, **placeholders: str) -> HomeAssistantError:
    """Return a translated error for a failure on the device or the network."""
    return HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key=key,
        translation_placeholders=placeholders or None,
    )


def validation_error(key: str, **placeholders: str) -> ServiceValidationError:
    """Return a translated error for invalid user input."""
    return ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key=key,
        translation_placeholders=placeholders or None,
    )


class TransferManager:
    """Operations on one kind of library file for one config entry.

    Every operation checks that the device is online first, and the store is
    changed only after the device confirmed the operation.
    """

    kind: str

    def __init__(
        self,
        hass: HomeAssistant,
        entry: CrossPointConfigEntry,
        coordinator: CrossPointDeviceCoordinator,
        store: TransferStore,
        root: Path,
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._coordinator = coordinator
        self._client = coordinator.client
        self._store = store
        self._root = root
        # Serialize whole operations so the store stays consistent.
        self._lock = asyncio.Lock()

    def normalize(self, file: str) -> str:
        """Return a safe path relative to the library subfolder, or raise."""
        rel = PurePosixPath(file.strip().lstrip("/"))
        if not rel.parts or ".." in rel.parts:
            raise validation_error("invalid_file", file=file)
        return rel.as_posix()

    def resolve(self, rel: str) -> Path:
        """Return the absolute path of a library file (blocking)."""
        root = self._root.resolve()
        path = (root / rel).resolve()
        if not path.is_relative_to(root):
            raise validation_error("invalid_file", file=rel)
        if not path.is_file():
            raise validation_error("file_not_found", file=rel)
        return path

    def read(self, rel: str) -> LocalFile:
        """Read a library file and hash it (blocking)."""
        path = self.resolve(rel)
        return LocalFile(path=path, data=path.read_bytes(), sha256=sha256_file(path))

    async def async_upload(
        self, rel: str, data: bytes, device_dir: str, filename: str, overwrite: bool
    ) -> str:
        """Upload bytes to the device and return the device path."""
        try:
            await self._client.ensure_dir(device_dir)
            return await self._client.upload(
                data,
                device_dir,
                filename,
                overwrite=overwrite,
                progress=self._progress_reporter(rel),
            )
        except CrossPointResponseError as err:
            if "exist" in str(err).lower():
                raise validation_error("file_exists_on_device", file=filename) from err
            raise translated_error("device_error", error=str(err)) from err
        except CrossPointError as err:
            self._coordinator.async_mark_connection_lost(err)
            raise translated_error("connection_lost", error=str(err)) from err

    async def async_record(
        self,
        rel: str,
        local: LocalFile,
        size: int,
        device_path: str,
    ) -> Transfer:
        """Record a confirmed transfer."""
        return await self._store.async_record(
            kind=self.kind,
            file=rel,
            sha256=local.sha256,
            size=size,
            sent_at=dt_util.utcnow(),
            device_path=device_path,
        )

    async def async_delete_on_device(
        self, device_path: str, *, forget_missing: bool
    ) -> None:
        """Delete a file on the device; tolerate it being gone if asked."""
        try:
            await self._client.delete(device_path)
        except CrossPointResponseError as err:
            if not await self._async_missing_on_device(device_path):
                raise translated_error("device_error", error=str(err)) from err
            if not forget_missing:
                raise validation_error("not_on_device", file=device_path) from err
        except CrossPointError as err:
            self._coordinator.async_mark_connection_lost(err)
            raise translated_error("connection_lost", error=str(err)) from err

    async def async_remove(self, file: str, *, forget_missing: bool = False) -> None:
        """Delete a tracked file from the device, then stop tracking it."""
        rel = self.normalize(file)
        async with self._lock:
            tracked = self._store.get(self.kind, rel)
            if tracked is None:
                raise validation_error("not_tracked", file=rel)
            await self._coordinator.async_ensure_online()
            await self.async_delete_on_device(
                tracked.device_path, forget_missing=forget_missing
            )
            await self._store.async_forget(self.kind, rel)

    async def _async_missing_on_device(self, device_path: str) -> bool:
        """Return True if the device listing confirms the file is gone."""
        parent, name = posixpath.split(device_path)
        try:
            files = await self._client.list_files(parent or "/")
        except CrossPointResponseError:
            return True  # the parent folder itself is gone
        return all(f.name != name for f in files)

    def _progress_reporter(self, rel: str) -> Callable[[int, int], None]:
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
                    "kind": self.kind,
                    "file": rel,
                    "received": received,
                    "total": total,
                },
            )

        return report


class BookManager(TransferManager):
    """Book operations for one config entry."""

    kind = KIND_BOOK

    def __init__(
        self,
        hass: HomeAssistant,
        entry: CrossPointConfigEntry,
        coordinator: CrossPointDeviceCoordinator,
        store: TransferStore,
    ) -> None:
        super().__init__(
            hass,
            entry,
            coordinator,
            store,
            Path(entry.data[CONF_LIBRARY_PATH]) / entry.data[CONF_BOOKS_DIR],
        )

    @property
    def device_dir(self) -> str:
        """Destination folder for books on the SD card."""
        return self._entry.options.get(CONF_DEVICE_BOOKS_DIR, DEFAULT_DEVICE_BOOKS_DIR)

    async def async_send(self, file: str, *, overwrite: bool = False) -> Transfer:
        """Upload a library book to the device and track it."""
        rel = self.normalize(file)
        async with self._lock:
            await self._coordinator.async_ensure_online()
            local = await self._hass.async_add_executor_job(self.read, rel)
            tracked = self._store.get(self.kind, rel)
            filename = local.path.name
            device_path = posixpath.join(self.device_dir, filename)
            # A tracked book is ours to replace (e.g. modified after sending).
            replace = overwrite or (
                tracked is not None and tracked.device_path == device_path
            )
            device_path = await self.async_upload(
                rel, local.data, self.device_dir, filename, replace
            )
            if tracked and tracked.device_path != device_path:
                _LOGGER.warning(
                    "%s was previously sent to %s; it is now at %s",
                    rel,
                    tracked.device_path,
                    device_path,
                )
            return await self.async_record(rel, local, len(local.data), device_path)

