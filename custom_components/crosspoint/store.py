"""Persistent tracking of the files sent to the device."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION = 1
_HASH_CHUNK = 1024 * 1024


@dataclass(frozen=True, slots=True)
class Transfer:
    """One file that the integration sent to the device."""

    kind: str
    file: str  # path relative to the kind's library subfolder
    sha256: str
    size: int
    sent_at: str  # ISO 8601, UTC
    device_path: str


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 of a file (blocking; run in the executor)."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_HASH_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


class TransferStore:
    """Track transfers in Home Assistant storage.

    Only files sent by the integration are tracked: the device content is never
    read back. Callers must record a transfer only after the device confirmed
    it, and forget it only after the device confirmed the deletion.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.transfers"
        )
        self._transfers: dict[str, Transfer] = {}

    @staticmethod
    def _key(kind: str, file: str) -> str:
        return f"{kind}:{file}"

    async def async_load(self) -> None:
        """Load the tracked transfers from disk."""
        data = await self._store.async_load() or {}
        self._transfers = {
            self._key(t["kind"], t["file"]): Transfer(**t)
            for t in data.get("transfers", [])
        }

    async def _async_save(self) -> None:
        await self._store.async_save(
            {"transfers": [asdict(t) for t in self._transfers.values()]}
        )

    def get(self, kind: str, file: str) -> Transfer | None:
        """Return the tracked transfer for a library file, if any."""
        return self._transfers.get(self._key(kind, file))

    def all(self, kind: str | None = None) -> list[Transfer]:
        """Return all tracked transfers, optionally of one kind."""
        return [t for t in self._transfers.values() if kind in (None, t.kind)]

    async def async_record(
        self,
        *,
        kind: str,
        file: str,
        sha256: str,
        size: int,
        sent_at: datetime,
        device_path: str,
    ) -> Transfer:
        """Record a confirmed transfer."""
        transfer = Transfer(
            kind=kind,
            file=file,
            sha256=sha256,
            size=size,
            sent_at=sent_at.isoformat(),
            device_path=device_path,
        )
        self._transfers[self._key(kind, file)] = transfer
        await self._async_save()
        return transfer

    async def async_forget(self, kind: str, file: str) -> None:
        """Forget a transfer after a confirmed deletion."""
        if self._transfers.pop(self._key(kind, file), None) is not None:
            await self._async_save()

    async def async_remove_all(self) -> None:
        """Delete the storage file (config entry removed)."""
        await self._store.async_remove()
