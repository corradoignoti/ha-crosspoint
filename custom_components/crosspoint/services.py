"""Services of the CrossPoint integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .wallpaper import MODE_NORMAL, MODES

if TYPE_CHECKING:
    from . import CrossPointConfigEntry

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_FILE = "file"
ATTR_OVERWRITE = "overwrite"
ATTR_FORGET_MISSING = "forget_missing"
ATTR_MODE = "mode"
ATTR_FORCE = "force"

SERVICE_SEND_BOOK = "send_book"
SERVICE_REMOVE_BOOK = "remove_book"
SERVICE_RESCAN_LIBRARY = "rescan_library"
SERVICE_REFRESH_READING_STATS = "refresh_reading_stats"
SERVICE_SEND_WALLPAPER = "send_wallpaper"
SERVICE_REMOVE_WALLPAPER = "remove_wallpaper"

_BASE = {
    vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
    vol.Required(ATTR_FILE): cv.string,
}
SEND_BOOK_SCHEMA = vol.Schema(
    {**_BASE, vol.Optional(ATTR_OVERWRITE, default=False): cv.boolean}
)
REMOVE_BOOK_SCHEMA = vol.Schema(
    {**_BASE, vol.Optional(ATTR_FORGET_MISSING, default=False): cv.boolean}
)
SEND_WALLPAPER_SCHEMA = vol.Schema(
    {
        **_BASE,
        vol.Optional(ATTR_MODE, default=MODE_NORMAL): vol.In(MODES),
        vol.Optional(ATTR_FORCE, default=False): cv.boolean,
    }
)
RESCAN_LIBRARY_SCHEMA = vol.Schema({vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string})


def _get_entry(hass: HomeAssistant, call: ServiceCall) -> CrossPointConfigEntry:
    entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="entry_not_found",
            translation_placeholders={"entry_id": entry_id},
        )
    if entry.state is not ConfigEntryState.LOADED:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="entry_not_loaded",
            translation_placeholders={"title": entry.title},
        )
    return entry


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the integration services."""

    async def send_book(call: ServiceCall) -> ServiceResponse:
        entry = _get_entry(hass, call)
        transfer = await entry.runtime_data.books.async_send(
            call.data[ATTR_FILE], overwrite=call.data[ATTR_OVERWRITE]
        )
        return {"device_path": transfer.device_path, "sha256": transfer.sha256}

    async def remove_book(call: ServiceCall) -> None:
        entry = _get_entry(hass, call)
        await entry.runtime_data.books.async_remove(
            call.data[ATTR_FILE], forget_missing=call.data[ATTR_FORGET_MISSING]
        )

    async def send_wallpaper(call: ServiceCall) -> ServiceResponse:
        entry = _get_entry(hass, call)
        transfer, transparent = await entry.runtime_data.wallpapers.async_send(
            call.data[ATTR_FILE],
            mode=call.data[ATTR_MODE],
            force=call.data[ATTR_FORCE],
        )
        return {
            "device_path": transfer.device_path,
            "sha256": transfer.sha256,
            "has_transparency": transparent,
        }

    async def remove_wallpaper(call: ServiceCall) -> None:
        entry = _get_entry(hass, call)
        await entry.runtime_data.wallpapers.async_remove(
            call.data[ATTR_FILE], forget_missing=call.data[ATTR_FORGET_MISSING]
        )

    async def refresh_reading_stats(call: ServiceCall) -> None:
        entry = _get_entry(hass, call)
        for coordinator in entry.runtime_data.stats.values():
            await coordinator.async_refresh()

    async def rescan_library(call: ServiceCall) -> None:
        entry = _get_entry(hass, call)
        await entry.runtime_data.library.async_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_BOOK,
        send_book,
        schema=SEND_BOOK_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REMOVE_BOOK, remove_book, schema=REMOVE_BOOK_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESCAN_LIBRARY,
        rescan_library,
        schema=RESCAN_LIBRARY_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_WALLPAPER,
        send_wallpaper,
        schema=SEND_WALLPAPER_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_WALLPAPER,
        remove_wallpaper,
        schema=REMOVE_BOOK_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_READING_STATS,
        refresh_reading_stats,
        schema=RESCAN_LIBRARY_SCHEMA,
    )
