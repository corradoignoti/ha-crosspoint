"""The CrossPoint integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
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
    SUBENTRY_SYNC_USER,
    DeviceModel,
)
from .coordinator import CrossPointDeviceCoordinator
from .library import LibraryCoordinator, async_remove_library_cache
from .panel import async_register_panel, async_unregister_panel
from .services import async_setup_services
from .stats import ReadingStatsCoordinator
from .store import TransferStore
from .transfers import BookManager, WallpaperManager, async_reconcile_device
from .views import CrossPointCoverView
from .websocket_api import async_setup_websocket_api

_LOGGER = logging.getLogger(__name__)

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
    wallpapers: WallpaperManager
    library: LibraryCoordinator
    stats: dict[str, ReadingStatsCoordinator]


type CrossPointConfigEntry = ConfigEntry[CrossPointRuntimeData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration-wide services, views and WebSocket commands."""
    async_setup_services(hass)
    async_setup_websocket_api(hass)
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
        wallpapers=WallpaperManager(hass, entry, coordinator, store),
        library=LibraryCoordinator(hass, entry, store),
        stats={
            subentry_id: ReadingStatsCoordinator(hass, entry, subentry)
            for subentry_id, subentry in entry.subentries.items()
            if subentry.subentry_type == SUBENTRY_SYNC_USER
        },
    )
    # An offline reader is a normal state, so the first refresh never fails.
    await coordinator.async_config_entry_first_refresh()
    await entry.runtime_data.library.async_config_entry_first_refresh()
    # Reading stats are independent: a sync server failure must not block the
    # e-reader, so their entities just start unavailable.
    for stats in entry.runtime_data.stats.values():
        await stats.async_refresh()

    _async_reconcile_when_online(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_register_panel(hass)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


def _async_reconcile_when_online(
    hass: HomeAssistant, entry: CrossPointConfigEntry
) -> None:
    """Reconcile the tracked files with the device each time it comes online."""
    coordinator = entry.runtime_data.coordinator
    was_online = False

    async def reconcile() -> None:
        try:
            result = await async_reconcile_device(entry)
        except HomeAssistantError as err:
            _LOGGER.debug("Reconciliation skipped: %s", err)
            return
        if result.removed or result.adopted:
            _LOGGER.info(
                "Reconciled with the device: %d removed, %d adopted",
                result.removed,
                result.adopted,
            )

    @callback
    def on_update() -> None:
        nonlocal was_online
        online = coordinator.online
        if online and not was_online:
            entry.async_create_background_task(
                hass, reconcile(), "crosspoint_reconcile"
            )
        was_online = online

    entry.async_on_unload(coordinator.async_add_listener(on_update))
    on_update()


async def async_unload_entry(hass: HomeAssistant, entry: CrossPointConfigEntry) -> bool:
    """Unload a config entry; remove the panel with the last one."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    others = [
        e
        for e in hass.config_entries.async_loaded_entries(DOMAIN)
        if e.entry_id != entry.entry_id
    ]
    if not others:
        async_unregister_panel(hass)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: CrossPointConfigEntry) -> None:
    """Delete the transfer history and library cache when the entry is removed."""
    await TransferStore(hass, entry.entry_id).async_remove_all()
    await async_remove_library_cache(hass, entry.entry_id)


async def _async_update_listener(
    hass: HomeAssistant, entry: CrossPointConfigEntry
) -> None:
    """Reload the entry when its options or reading stats users change."""
    hass.config_entries.async_schedule_reload(entry.entry_id)
