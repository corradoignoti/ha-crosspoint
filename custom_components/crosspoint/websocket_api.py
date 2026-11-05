"""WebSocket commands used by the CrossPoint sidebar panel."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.http.auth import async_sign_path
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, EVENT_UPLOAD_PROGRESS, KIND_BOOK, KIND_WALLPAPER
from .wallpaper import MODE_NORMAL, MODES

if TYPE_CHECKING:
    from . import CrossPointConfigEntry

# Signed thumbnail URLs stay valid this long; state updates re-sign them.
THUMBNAIL_URL_LIFETIME = timedelta(hours=12)


@callback
def async_setup_websocket_api(hass: HomeAssistant) -> None:
    """Register the panel commands."""
    for command in (
        ws_entries,
        ws_subscribe,
        ws_send_book,
        ws_remove_book,
        ws_send_wallpaper,
        ws_remove_wallpaper,
        ws_wallpaper_check,
        ws_rescan,
    ):
        websocket_api.async_register_command(hass, command)


def _loaded_entries(hass: HomeAssistant) -> list[CrossPointConfigEntry]:
    return [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]


def _get_entry(hass: HomeAssistant, entry_id: str) -> CrossPointConfigEntry:
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="entry_not_found",
            translation_placeholders={"entry_id": entry_id},
        )
    if entry.state is not ConfigEntryState.LOADED:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="entry_not_loaded",
            translation_placeholders={"title": entry.title},
        )
    return entry


def _state(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    entry: CrossPointConfigEntry,
) -> dict[str, Any]:
    """Build the full panel state of one entry."""
    runtime = entry.runtime_data
    device = runtime.coordinator.data

    def items(kind: str) -> list[dict[str, Any]]:
        result = []
        for item in runtime.library.items(kind):
            data = item.as_dict()
            if item.entry and item.entry.has_cover:
                data["thumbnail_url"] = async_sign_path(
                    hass,
                    f"/api/crosspoint/{entry.entry_id}/cover/{item.entry.sha256}",
                    THUMBNAIL_URL_LIFETIME,
                    refresh_token_id=connection.refresh_token_id,
                )
            if item.transfer:
                data["mode"] = item.transfer.mode
            result.append(data)
        return result

    return {
        "entry_id": entry.entry_id,
        "title": entry.title,
        "host": runtime.client.host,
        "model": {
            "name": runtime.model.name,
            "width": runtime.model.width,
            "height": runtime.model.height,
        },
        "online": runtime.coordinator.online,
        "firmware": device.status.get("version") if device else None,
        "books_dir": runtime.books.device_dir,
        "books": items(KIND_BOOK),
        "wallpapers": items(KIND_WALLPAPER),
    }


@websocket_api.websocket_command({vol.Required("type"): "crosspoint/entries"})
@websocket_api.require_admin
@callback
def ws_entries(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """List the loaded CrossPoint e-readers."""
    connection.send_result(
        msg["id"],
        [
            {
                "entry_id": entry.entry_id,
                "title": entry.title,
                "online": entry.runtime_data.coordinator.online,
            }
            for entry in _loaded_entries(hass)
        ],
    )


@websocket_api.websocket_command(
    {vol.Required("type"): "crosspoint/subscribe", vol.Required("entry_id"): str}
)
@websocket_api.require_admin
@callback
def ws_subscribe(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Stream the panel state and upload progress of one e-reader.

    Sends ``{"type": "state", ...}`` now and after every change,
    ``{"type": "progress", ...}`` during uploads, and ``{"type": "closed"}``
    when the entry is unloaded (the panel should subscribe again).
    """
    try:
        entry = _get_entry(hass, msg["entry_id"])
    except HomeAssistantError as err:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, str(err))
        return
    msg_id = msg["id"]
    runtime = entry.runtime_data
    unsubs: list[Any] = []

    @callback
    def send_state() -> None:
        connection.send_message(
            websocket_api.event_message(
                msg_id, {"type": "state", **_state(hass, connection, entry)}
            )
        )

    @callback
    def forward_progress(event: Event) -> None:
        if event.data.get("entry_id") == entry.entry_id:
            connection.send_message(
                websocket_api.event_message(msg_id, {"type": "progress", **event.data})
            )

    @callback
    def unsubscribe() -> None:
        while unsubs:
            unsubs.pop()()

    @callback
    def on_unload() -> None:
        unsubscribe()
        connection.subscriptions.pop(msg_id, None)
        connection.send_message(websocket_api.event_message(msg_id, {"type": "closed"}))

    unsubs.append(runtime.library.async_add_listener(send_state))
    unsubs.append(runtime.coordinator.async_add_listener(send_state))
    unsubs.append(hass.bus.async_listen(EVENT_UPLOAD_PROGRESS, forward_progress))
    entry.async_on_unload(on_unload)
    connection.subscriptions[msg_id] = unsubscribe
    connection.send_result(msg_id)
    send_state()


def _action(schema: dict, handler):
    """Wrap an admin-only async command that returns a result."""

    @websocket_api.websocket_command({**schema, vol.Required("entry_id"): str})
    @websocket_api.require_admin
    @websocket_api.async_response
    async def command(
        hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
    ) -> None:
        entry = _get_entry(hass, msg["entry_id"])
        connection.send_result(msg["id"], await handler(entry, msg))

    return command


async def _send_book(entry: CrossPointConfigEntry, msg: dict) -> dict:
    transfer = await entry.runtime_data.books.async_send(
        msg["file"], overwrite=msg["overwrite"]
    )
    return {"device_path": transfer.device_path}


async def _remove_book(entry: CrossPointConfigEntry, msg: dict) -> None:
    await entry.runtime_data.books.async_remove(
        msg["file"], forget_missing=msg["forget_missing"]
    )


async def _send_wallpaper(entry: CrossPointConfigEntry, msg: dict) -> dict:
    transfer, transparent = await entry.runtime_data.wallpapers.async_send(
        msg["file"], mode=msg["mode"], force=msg["force"]
    )
    return {"device_path": transfer.device_path, "has_transparency": transparent}


async def _remove_wallpaper(entry: CrossPointConfigEntry, msg: dict) -> None:
    await entry.runtime_data.wallpapers.async_remove(
        msg["file"], forget_missing=msg["forget_missing"]
    )


async def _wallpaper_check(entry: CrossPointConfigEntry, msg: dict) -> dict:
    return {
        "has_transparency": await entry.runtime_data.wallpapers.async_check(msg["file"])
    }


async def _rescan(entry: CrossPointConfigEntry, msg: dict) -> None:
    await entry.runtime_data.library.async_refresh()


_FILE = {vol.Required("file"): str}
_FORGET = {vol.Optional("forget_missing", default=False): bool}

ws_send_book = _action(
    {
        vol.Required("type"): "crosspoint/send_book",
        **_FILE,
        vol.Optional("overwrite", default=False): bool,
    },
    _send_book,
)
ws_remove_book = _action(
    {vol.Required("type"): "crosspoint/remove_book", **_FILE, **_FORGET},
    _remove_book,
)
ws_send_wallpaper = _action(
    {
        vol.Required("type"): "crosspoint/send_wallpaper",
        **_FILE,
        vol.Optional("mode", default=MODE_NORMAL): vol.In(MODES),
        vol.Optional("force", default=False): bool,
    },
    _send_wallpaper,
)
ws_remove_wallpaper = _action(
    {vol.Required("type"): "crosspoint/remove_wallpaper", **_FILE, **_FORGET},
    _remove_wallpaper,
)
ws_wallpaper_check = _action(
    {vol.Required("type"): "crosspoint/wallpaper_check", **_FILE},
    _wallpaper_check,
)
ws_rescan = _action({vol.Required("type"): "crosspoint/rescan"}, _rescan)
