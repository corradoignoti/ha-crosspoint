"""The CrossPoint integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api.device import CrossPointDeviceClient
from .const import CONF_MODEL, CONF_WS_PORT, DEFAULT_WS_PORT, MODELS, DeviceModel


@dataclass(slots=True)
class CrossPointRuntimeData:
    """Objects shared by the platforms of one config entry."""

    client: CrossPointDeviceClient
    model: DeviceModel


type CrossPointConfigEntry = ConfigEntry[CrossPointRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: CrossPointConfigEntry) -> bool:
    """Set up CrossPoint from a config entry."""
    client = CrossPointDeviceClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        ws_port=entry.data.get(CONF_WS_PORT, DEFAULT_WS_PORT),
    )
    entry.runtime_data = CrossPointRuntimeData(
        client=client, model=MODELS[entry.data[CONF_MODEL]]
    )
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CrossPointConfigEntry) -> bool:
    """Unload a config entry."""
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: CrossPointConfigEntry
) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
