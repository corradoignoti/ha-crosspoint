"""Tests for the panel WebSocket API and panel registration."""

from __future__ import annotations

import io

import pytest
from homeassistant.components import frontend
from homeassistant.core import HomeAssistant
from PIL import Image

from .epub_factory import make_epub

pytestmark = pytest.mark.usefixtures("socket_enabled")


@pytest.fixture
def library(tmp_path):
    (tmp_path / "books").mkdir()
    make_epub(tmp_path / "books" / "Dune.epub")
    (tmp_path / "wallpapers").mkdir()
    buf = io.BytesIO()
    Image.new("RGB", (800, 600), "gray").save(buf, "PNG")
    (tmp_path / "wallpapers" / "sea.png").write_bytes(buf.getvalue())
    return tmp_path


@pytest.fixture
async def entry(setup_device_entry, library):
    return await setup_device_entry()


async def test_panel_registered_and_removed(hass: HomeAssistant, entry):
    assert "crosspoint" in hass.data[frontend.DATA_PANELS]
    panel = hass.data[frontend.DATA_PANELS]["crosspoint"]
    assert panel.require_admin is True
    await hass.config_entries.async_unload(entry.entry_id)
    assert "crosspoint" not in hass.data[frontend.DATA_PANELS]


async def test_stats_card_loaded(hass: HomeAssistant, entry):
    urls = hass.data[frontend.DATA_EXTRA_MODULE_URL].urls
    assert any("/crosspoint_static/crosspoint-stats-card.js" in url for url in urls)


async def test_entries(hass: HomeAssistant, entry, hass_ws_client):
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "crosspoint/entries"})
    msg = await client.receive_json()
    assert msg["result"] == [
        {"entry_id": entry.entry_id, "title": "CrossPoint", "online": True}
    ]


async def test_subscribe_send_and_progress(hass: HomeAssistant, entry, hass_ws_client):
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "crosspoint/subscribe", "entry_id": entry.entry_id}
    )
    assert (await client.receive_json())["success"]
    state = (await client.receive_json())["event"]
    assert state["type"] == "state"
    assert state["online"] is True
    assert state["model"] == {"name": "Xteink X4", "width": 480, "height": 800}
    [book] = state["books"]
    assert book["status"] == "not_installed"
    assert book["title"] == "Dune"
    assert "authSig=" in book["thumbnail_url"]
    assert "authSig=" in state["wallpapers"][0]["thumbnail_url"]

    await client.send_json_auto_id(
        {
            "type": "crosspoint/send_book",
            "entry_id": entry.entry_id,
            "file": "Dune.epub",
        }
    )
    seen_progress = installed = False
    result = None
    while result is None or not installed:
        msg = await client.receive_json()
        if msg["type"] == "result":
            result = msg
        elif msg["event"]["type"] == "progress":
            seen_progress = True
        elif msg["event"]["type"] == "state":
            installed = msg["event"]["books"][0]["status"] == "installed"
    assert result["success"]
    assert result["result"] == {"device_path": "/Books/Dune.epub"}
    assert seen_progress


async def test_subscription_closed_on_unload(hass, entry, hass_ws_client):
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "crosspoint/subscribe", "entry_id": entry.entry_id}
    )
    await client.receive_json()
    await client.receive_json()
    await hass.config_entries.async_unload(entry.entry_id)
    msg = await client.receive_json()
    assert msg["event"] == {"type": "closed"}


async def test_errors_are_translated(hass, entry, hass_ws_client, device):
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "crosspoint/remove_book", "entry_id": entry.entry_id, "file": "x"}
    )
    msg = await client.receive_json()
    assert msg["success"] is False
    assert msg["error"]["translation_key"] == "not_tracked"

    await client.send_json_auto_id(
        {"type": "crosspoint/send_book", "entry_id": "missing", "file": "x"}
    )
    msg = await client.receive_json()
    assert msg["error"]["translation_key"] == "entry_not_found"


async def test_wallpaper_commands(hass, entry, hass_ws_client):
    client = await hass_ws_client(hass)
    base = {"entry_id": entry.entry_id, "file": "sea.png"}
    await client.send_json_auto_id({"type": "crosspoint/wallpaper_check", **base})
    assert (await client.receive_json())["result"] == {"has_transparency": False}

    await client.send_json_auto_id(
        {"type": "crosspoint/send_wallpaper", **base, "mode": "transparent"}
    )
    msg = await client.receive_json()
    assert msg["error"]["translation_key"] == "no_transparency"

    await client.send_json_auto_id({"type": "crosspoint/send_wallpaper", **base})
    msg = await client.receive_json()
    assert msg["result"]["device_path"].startswith("/.sleep/")

    await client.send_json_auto_id({"type": "crosspoint/remove_wallpaper", **base})
    assert (await client.receive_json())["success"]

    await client.send_json_auto_id(
        {"type": "crosspoint/rescan", "entry_id": entry.entry_id}
    )
    assert (await client.receive_json())["success"]


async def test_requires_admin(hass, entry, hass_ws_client, hass_admin_user):
    hass_admin_user.groups = []
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "crosspoint/entries"})
    msg = await client.receive_json()
    assert msg["error"]["code"] == "unauthorized"
