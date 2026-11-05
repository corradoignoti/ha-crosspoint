"""Tests for the library scan, sensors, rescan service and cover view."""

from __future__ import annotations

from datetime import UTC, datetime
from http import HTTPStatus
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.crosspoint.api.errors import CrossPointConnectionError
from custom_components.crosspoint.const import (
    CONF_BOOKS_DIR,
    CONF_LIBRARY_PATH,
    CONF_MODEL,
    CONF_WALLPAPERS_DIR,
    DOMAIN,
)
from custom_components.crosspoint.library import (
    STATUS_INSTALLED,
    STATUS_MISSING,
    STATUS_MODIFIED,
    STATUS_NOT_INSTALLED,
)

from .epub_factory import make_epub, png

GET_STATUS = "custom_components.crosspoint.api.device.CrossPointDeviceClient.get_status"
LIBRARY = "sensor.xteink_x4_library_books"
INSTALLED = "sensor.xteink_x4_books_on_device"


@pytest.fixture
def library(tmp_path):
    books = tmp_path / "books"
    (books / "Sci-Fi").mkdir(parents=True)
    make_epub(books / "Dune.epub")
    make_epub(books / "Sci-Fi" / "Foundation.epub", title="Foundation", cover=None)
    (books / "notes.txt").write_text("ignored")
    (books / ".hidden.epub").write_text("ignored")
    wallpapers = tmp_path / "wallpapers"
    wallpapers.mkdir()
    (wallpapers / "sea.png").write_bytes(png("blue", (100, 100)))
    return tmp_path


@pytest.fixture
async def entry(hass: HomeAssistant, library):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="crosspoint.local",
        title="CrossPoint",
        data={
            "host": "crosspoint.local",
            CONF_MODEL: "xteink_x4",
            CONF_LIBRARY_PATH: str(library),
            CONF_BOOKS_DIR: "books",
            CONF_WALLPAPERS_DIR: "wallpapers",
        },
    )
    entry.add_to_hass(hass)
    with patch(GET_STATUS, AsyncMock(side_effect=CrossPointConnectionError("x"))):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def _statuses(entry):
    return {i.file: i.status for i in entry.runtime_data.library.items("book")}


async def test_scan(hass: HomeAssistant, entry):
    data = entry.runtime_data.library.data
    assert set(data.books) == {"Dune.epub", "Sci-Fi/Foundation.epub"}
    assert set(data.wallpapers) == {"sea.png"}
    dune = data.books["Dune.epub"]
    assert (dune.title, dune.authors, dune.has_cover) == (
        "Dune",
        ("Frank Herbert",),
        True,
    )
    assert data.books["Sci-Fi/Foundation.epub"].has_cover is False
    assert hass.states.get(LIBRARY).state == "2"
    assert hass.states.get(INSTALLED).state == "0"


async def test_status_follows_transfers(hass: HomeAssistant, entry, library):
    runtime = entry.runtime_data
    dune = runtime.library.data.books["Dune.epub"]
    record = {
        "kind": "book",
        "size": 1,
        "sent_at": datetime(2026, 1, 1, tzinfo=UTC),
        "device_path": "/Books/x.epub",
    }
    await runtime.store.async_record(file="Dune.epub", sha256=dune.sha256, **record)
    await runtime.store.async_record(
        file="Sci-Fi/Foundation.epub", sha256="old", **record
    )
    await runtime.store.async_record(file="Gone.epub", sha256="x", **record)
    await hass.async_block_till_done()

    assert _statuses(entry) == {
        "Dune.epub": STATUS_INSTALLED,
        "Sci-Fi/Foundation.epub": STATUS_MODIFIED,
        "Gone.epub": STATUS_MISSING,
    }
    state = hass.states.get(INSTALLED)
    assert state.state == "3"
    assert state.attributes["modified"] == 1
    assert state.attributes["missing_from_library"] == 1

    await runtime.store.async_forget("book", "Dune.epub")
    await hass.async_block_till_done()
    assert _statuses(entry)["Dune.epub"] == STATUS_NOT_INSTALLED
    assert hass.states.get(INSTALLED).state == "2"


async def test_rescan_uses_cache(hass: HomeAssistant, entry, library):
    make_epub(library / "books" / "New.epub", title="New")
    with patch(
        "custom_components.crosspoint.library.sha256_file",
        wraps=__import__(
            "custom_components.crosspoint.store", fromlist=["sha256_file"]
        ).sha256_file,
    ) as hashed:
        await hass.services.async_call(
            DOMAIN,
            "rescan_library",
            {"config_entry_id": entry.entry_id},
            blocking=True,
        )
    assert hashed.call_count == 1  # only the new file
    await hass.async_block_till_done()
    assert hass.states.get(LIBRARY).state == "3"

    (library / "books" / "Dune.epub").unlink()
    await entry.runtime_data.library.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(LIBRARY).state == "2"
    new = entry.runtime_data.library.data.books["New.epub"]
    covers = entry.runtime_data.library.covers_dir.glob("*.jpg")
    assert [c.name for c in covers] == [f"{new.sha256}.jpg"]


async def test_cover_view(hass: HomeAssistant, entry, hass_client):
    assert await async_setup_component(hass, "http", {})
    client = await hass_client()
    dune = entry.runtime_data.library.data.books["Dune.epub"]
    url = f"/api/crosspoint/{entry.entry_id}/cover/{dune.sha256}"
    resp = await client.get(url)
    assert resp.status == HTTPStatus.OK
    assert resp.headers["Content-Type"] == "image/jpeg"
    assert (await resp.read())[:2] == b"\xff\xd8"

    no_cover = entry.runtime_data.library.data.books["Sci-Fi/Foundation.epub"]
    for bad in (no_cover.sha256, "../etc", "0" * 64):
        resp = await client.get(f"/api/crosspoint/{entry.entry_id}/cover/{bad}")
        assert resp.status == HTTPStatus.NOT_FOUND


async def test_cover_view_requires_auth(
    hass: HomeAssistant, entry, hass_client_no_auth
):
    client = await hass_client_no_auth()
    dune = entry.runtime_data.library.data.books["Dune.epub"]
    resp = await client.get(f"/api/crosspoint/{entry.entry_id}/cover/{dune.sha256}")
    assert resp.status == HTTPStatus.UNAUTHORIZED


async def test_remove_entry_clears_cache(hass: HomeAssistant, entry, hass_storage):
    covers = entry.runtime_data.library.covers_dir
    assert covers.is_dir()
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert not covers.exists()
    assert f"{DOMAIN}.{entry.entry_id}.library" not in hass_storage
