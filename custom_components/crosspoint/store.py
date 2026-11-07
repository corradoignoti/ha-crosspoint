"""Persistent tracking of the files sent to the device."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
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
    mode: str | None = None  # wallpaper conversion mode
    device_id: str | None = None  # reader that received the file


@dataclass(slots=True)
class KnownDevice:
    """A reader that was seen connected to this config entry."""

    device_id: str
    model: str | None
    first_seen: str
    last_seen: str
    last_ip: str | None = None


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
        self._devices: dict[str, KnownDevice] = {}
        self._active_device: str | None = None
        self._listeners: list[Callable[[], None]] = []

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> CALLBACK_TYPE:
        """Call ``listener`` after every change; return a function to remove it."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def _key(self, kind: str, file: str, device_id: str | None = ...) -> str:
        device = self._active_device if device_id is ... else device_id
        return f"{device or ''}|{kind}:{file}"

    @property
    def active_device(self) -> str | None:
        """Return the ID of the reader currently connected, if known."""
        return self._active_device

    @property
    def devices(self) -> list[KnownDevice]:
        """Return the readers seen so far, most recently seen first."""
        return sorted(self._devices.values(), key=lambda d: d.last_seen, reverse=True)

    async def async_set_active_device(
        self, device_id: str | None, model: str | None, ip: str | None, now: datetime
    ) -> None:
        """Select the reader whose transfers are tracked from now on.

        Transfers recorded before readers were identified (no device ID) are
        assigned to the first reader that gets identified.
        """
        if device_id is None:
            return  # firmware without an identifier: keep the current selection
        changed = device_id != self._active_device
        known = self._devices.get(device_id)
        stamp = now.isoformat()
        if known is None:
            self._devices[device_id] = KnownDevice(device_id, model, stamp, stamp, ip)
            changed = True
            if not self._devices.keys() - {device_id}:
                self._adopt_legacy(device_id)
        else:
            if known.last_ip != ip or known.model != model:
                known.last_ip, known.model = ip, model
                changed = True
            known.last_seen = stamp
        self._active_device = device_id
        # last_seen alone is not worth a write: it is saved with the next change.
        if changed:
            await self._async_save()

    def _adopt_legacy(self, device_id: str) -> None:
        self._transfers = {
            self._key(t.kind, t.file, device_id): replace(t, device_id=device_id)
            if t.device_id is None
            else t
            for t in self._transfers.values()
        }

    async def async_load(self) -> None:
        """Load the tracked transfers from disk."""
        data = await self._store.async_load() or {}
        self._transfers = {}
        for raw in data.get("transfers", []):
            transfer = Transfer(**raw)
            self._transfers[
                self._key(transfer.kind, transfer.file, transfer.device_id)
            ] = transfer
        self._devices = {
            raw["device_id"]: KnownDevice(**raw) for raw in data.get("devices", [])
        }
        self._active_device = data.get("active_device")

    async def _async_save(self) -> None:
        await self._store.async_save(
            {
                "transfers": [asdict(t) for t in self._transfers.values()],
                "devices": [asdict(d) for d in self._devices.values()],
                "active_device": self._active_device,
            }
        )
        for listener in list(self._listeners):
            listener()

    def get(self, kind: str, file: str) -> Transfer | None:
        """Return the tracked transfer of a library file on the active reader."""
        return self._transfers.get(self._key(kind, file))

    def all(self, kind: str | None = None) -> list[Transfer]:
        """Return the transfers on the active reader, optionally of one kind."""
        return [
            t
            for t in self._transfers.values()
            if kind in (None, t.kind) and t.device_id == self._active_device
        ]

    def installed_on(self, kind: str, file: str) -> list[str]:
        """Return the IDs of all known readers holding a library file."""
        return [
            d.device_id
            for d in self.devices
            if self._key(kind, file, d.device_id) in self._transfers
        ]

    async def async_record(
        self,
        *,
        kind: str,
        file: str,
        sha256: str,
        size: int,
        sent_at: datetime,
        device_path: str,
        mode: str | None = None,
    ) -> Transfer:
        """Record a confirmed transfer."""
        transfer = Transfer(
            kind=kind,
            file=file,
            sha256=sha256,
            size=size,
            sent_at=sent_at.isoformat(),
            device_path=device_path,
            mode=mode,
            device_id=self._active_device,
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
