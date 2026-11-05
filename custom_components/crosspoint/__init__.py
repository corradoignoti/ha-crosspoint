"""The CrossPoint integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api.device import CrossPointDeviceClient
from .const import (
    CONF_MODEL,
    CONF_WS_PORT,
    DEFAULT_WS_PORT,
    DOMAIN,
    MODELS,
    DeviceModel,
)
from .coordinator import CrossPointDeviceCoordinator
from .library import LibraryCoordinator, async_remove_library_cache
from .services import async_setup_services
from .store import TransferStore
from .transfers import BookManager
from .views import CrossPointCoverView

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass(slots=True)
class CrossPointRuntimeData:
    """Objects shared by the platforms of one config entry."""

    client: CrossPointDeviceClient
    model: DeviceModel
    coordinator: CrossPointDeviceCoordinator
    store: TransferStore
    books: BookManager
    library: LibraryCoordinator


type CrossPointConfigEntry = ConfigEntry[CrossPointRuntimeData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration-wide services and views."""
    async_setup_services(hass)
    hass.http.register_view(CrossPointCoverView())
    return True


async def async_setup_entry(hass: HomeAssistant, entry: CrossPointConfigEntry) -> bool:
    """Set up CrossPoint from a config entry."""
    client = CrossPointDeviceClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        ws_port=entry.data.get(CONF_WS_PORT, DEFAULT_WS_PORT),
    )
    coordinator = CrossPointDeviceCoordinator(hass, entry, client)
    store = TransferStore(hass, entry.entry_id)
    await store.async_load()
    entry.runtime_data = CrossPointRuntimeData(
        client=client,
        model=MODELS[entry.data[CONF_MODEL]],
        coordinator=coordinator,
        store=store,
        books=BookManager(hass, entry, coordinator, store),
        library=LibraryCoordinator(hass, entry, store),
    )
    # An offline reader is a normal state, so the first refresh never fails.
    await coordinator.async_config_entry_first_refresh()
    await entry.runtime_data.library.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CrossPointConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: CrossPointConfigEntry) -> None:
    """Delete the transfer history and library cache when the entry is removed."""
    await TransferStore(hass, entry.entry_id).async_remove_all()
    await async_remove_library_cache(hass, entry.entry_id)


async def _async_update_listener(
    hass: HomeAssistant, entry: CrossPointConfigEntry
) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
