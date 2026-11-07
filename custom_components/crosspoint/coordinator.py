"""Coordinators for the CrossPoint integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .api.device import CrossPointDeviceClient
from .api.errors import CrossPointConnectionError, CrossPointError
from .const import DEVICE_ID_PLUGIN, DEVICE_POLL_INTERVAL_S, DOMAIN

if TYPE_CHECKING:
    from . import CrossPointConfigEntry

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DeviceState:
    """Last known reachability of the e-reader web server."""

    online: bool
    status: dict[str, Any] = field(default_factory=dict)

    @property
    def device_id(self) -> str | None:
        """Stable ID of the connected unit, if the firmware reports one."""
        value = self.status.get("deviceId")
        return str(value) if value else None


class CrossPointDeviceCoordinator(DataUpdateCoordinator[DeviceState]):
    """Poll the e-reader to know whether its web server is reachable.

    The web server runs only while the reader is in File Transfer (or Calibre
    Wireless) mode, so being offline is a normal state, not an update failure:
    entities stay available and report ``online = False``.
    """

    config_entry: CrossPointConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: CrossPointConfigEntry,
        client: CrossPointDeviceClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} device {client.host}",
            update_interval=timedelta(seconds=DEVICE_POLL_INTERVAL_S),
            always_update=False,
        )
        self.client = client

    @property
    def online(self) -> bool:
        """Return True if the last probe reached the device."""
        return self.data is not None and self.data.online

    async def _async_update_data(self) -> DeviceState:
        return await self._async_probe()

    async def _async_probe(self) -> DeviceState:
        was_online = self.online
        try:
            status = await self.client.get_status(plugin=DEVICE_ID_PLUGIN)
        except CrossPointError as err:
            if was_online:
                _LOGGER.info("CrossPoint at %s went offline", self.client.host)
            _LOGGER.debug("CrossPoint at %s not reachable: %s", self.client.host, err)
            return DeviceState(online=False)

        if not was_online:
            _LOGGER.info("CrossPoint at %s is online", self.client.host)
        self._update_device_registry(status)
        state = DeviceState(online=True, status=status)
        await self.config_entry.runtime_data.store.async_set_active_device(
            state.device_id,
            status.get("device"),
            status.get("ip"),
            dt_util.utcnow(),
        )
        return state

    def _update_device_registry(self, status: dict[str, Any]) -> None:
        version = status.get("version")
        if not version:
            return
        registry = dr.async_get(self.hass)
        device = registry.async_get_device_by_identifier(
            (DOMAIN, self.config_entry.entry_id), self.config_entry.entry_id
        )
        if device and device.sw_version != version:
            registry.async_update_device(device.id, sw_version=str(version))

    async def async_ensure_online(self) -> None:
        """Probe the device now and raise if it cannot be reached.

        Every operation on books or wallpapers must call this first, so that
        nothing is attempted while the device is offline.
        """
        state = await self._async_probe()
        if state != self.data:
            self.async_set_updated_data(state)
        if not state.online:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="device_offline",
                translation_placeholders={"host": self.client.host},
            )

    def async_mark_connection_lost(self, err: CrossPointError) -> None:
        """Mark the device offline after a connection failure mid-operation."""
        if isinstance(err, CrossPointConnectionError) and self.online:
            self.async_set_updated_data(DeviceState(online=False))
