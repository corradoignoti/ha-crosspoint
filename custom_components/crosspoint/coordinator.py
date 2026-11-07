"""Coordinators for the CrossPoint integration."""

from __future__ import annotations

import logging
import time
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
from .const import (
    DEVICE_ID_PLUGIN,
    DEVICE_POLL_INTERVAL_S,
    DOMAIN,
    MODELS,
    REDISCOVERY_INTERVAL_S,
    guess_model,
)
from .discovery import async_discover

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
        """Stable ID of the connected unit, if the firmware reports one.

        ``deviceId`` is preferred; the hardware ``serial`` is the fallback
        when the firmware cannot derive it (e.g. NVS unavailable).
        """
        if value := self.status.get("deviceId"):
            return str(value)
        if serial := self.status.get("serial"):
            return f"serial:{serial}"
        return None


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
        self._last_discovery: float | None = None

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
            status = await self._async_rediscover()
            if status is None:
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
        registry = dr.async_get(self.hass)
        device = registry.async_get_device_by_identifier(
            (DOMAIN, self.config_entry.entry_id), self.config_entry.entry_id
        )
        if device is None:
            return
        changes: dict[str, str] = {}
        if (version := status.get("version")) and device.sw_version != str(version):
            changes["sw_version"] = str(version)
        if key := guess_model(status.get("device")):
            name = MODELS[key].name
            if device.model != name:
                changes["model"] = name
                if device.name_by_user is None:
                    changes["name"] = name
        if changes:
            registry.async_update_device(device.id, **changes)

    async def _async_rediscover(self) -> dict[str, Any] | None:
        """Look for a reader on the network when the known address fails.

        Readers usually get their address from DHCP, so another reader (or the
        same one after a reconnection) can answer on a different IP. Discovery
        is throttled because each broadcast waits for replies.
        """
        now = time.monotonic()
        if (
            self._last_discovery is not None
            and now - self._last_discovery < REDISCOVERY_INTERVAL_S
        ):
            return None
        self._last_discovery = now
        previous = (self.client.host, self.client.ws_port)
        for device in await async_discover():
            if device.host == previous[0]:
                continue
            self.client.set_address(device.host, device.ws_port)
            try:
                status = await self.client.get_status(plugin=DEVICE_ID_PLUGIN)
            except CrossPointError:
                continue
            _LOGGER.info(
                "CrossPoint not reachable at %s; found a reader at %s",
                previous[0],
                device.host,
            )
            return status
        self.client.set_address(*previous)
        return None

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
