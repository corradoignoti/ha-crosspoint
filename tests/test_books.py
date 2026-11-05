"""End-to-end tests of book operations against the fake firmware server."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
)

from custom_components.crosspoint.api.device import CrossPointDeviceClient
from custom_components.crosspoint.const import (
    CONF_BOOKS_DIR,
    CONF_LIBRARY_PATH,
    CONF_MODEL,
    CONF_WALLPAPERS_DIR,
    DOMAIN,
    EVENT_UPLOAD_PROGRESS,
)

from .fake_device import FakeCrossPoint

pytestmark = pytest.mark.usefixtures("socket_enabled")


@pytest.fixture
async def device():
    fake = FakeCrossPoint()
    await fake.start()
    yield fake
    await fake.close()


@pytest.fixture
def books(tmp_path):
    root = tmp_path / "books"
    root.mkdir()
    (root / "Dune.epub").write_bytes(b"dune v1" * 1000)
    return root


@pytest.fixture
async def entry(hass: HomeAssistant, device, books, tmp_path):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="crosspoint.local",
        title="CrossPoint",
        data={
            "host": "crosspoint.local",
            CONF_MODEL: "xteink_x4",
            CONF_LIBRARY_PATH: str(tmp_path),
            CONF_BOOKS_DIR: "books",
            CONF_WALLPAPERS_DIR: "wallpapers",
        },
    )
    entry.add_to_hass(hass)

    def make_client(session, host, ws_port):
        return CrossPointDeviceClient(
            session, "127.0.0.1", http_port=device.http.port, ws_port=device.ws.port
        )

    with patch("custom_components.crosspoint.CrossPointDeviceClient", make_client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def _call(hass, service, entry, **data):
    return await hass.services.async_call(
        DOMAIN,
        service,
        {"config_entry_id": entry.entry_id, **data},
        blocking=True,
        return_response=service == "send_book",
    )


async def test_send_and_remove(hass: HomeAssistant, entry, device, books):
    events = async_capture_events(hass, EVENT_UPLOAD_PROGRESS)
    response = await _call(hass, "send_book", entry, file="Dune.epub")
    assert response["device_path"] == "/Books/Dune.epub"
    assert device.files["/Books/Dune.epub"] == (books / "Dune.epub").read_bytes()
    assert events[-1].data["received"] == events[-1].data["total"]
    tracked = entry.runtime_data.store.get("book", "Dune.epub")
    assert tracked.sha256 == response["sha256"]

    await _call(hass, "remove_book", entry, file="Dune.epub")
    assert "/Books/Dune.epub" not in device.files
    assert entry.runtime_data.store.get("book", "Dune.epub") is None


async def test_resend_modified_book_overwrites(hass, entry, device, books):
    first = await _call(hass, "send_book", entry, file="Dune.epub")
    (books / "Dune.epub").write_bytes(b"dune v2")
    second = await _call(hass, "send_book", entry, file="Dune.epub")
    assert device.files["/Books/Dune.epub"] == b"dune v2"
    assert first["sha256"] != second["sha256"]


async def test_untracked_file_on_device(hass, entry, device):
    device.dirs.add("/Books")
    device.files["/Books/Dune.epub"] = b"someone else's"
    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, "send_book", entry, file="Dune.epub")
    assert err.value.translation_key == "file_exists_on_device"
    assert entry.runtime_data.store.all() == []

    await _call(hass, "send_book", entry, file="Dune.epub", overwrite=True)
    assert device.files["/Books/Dune.epub"].startswith(b"dune v1")


async def test_offline_blocks_operations(hass, entry, device):
    await device.close()
    with pytest.raises(HomeAssistantError) as err:
        await _call(hass, "send_book", entry, file="Dune.epub")
    assert err.value.translation_key == "device_offline"
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.xteink_x4_online").state == STATE_OFF
    assert entry.runtime_data.store.all() == []


async def test_failed_upload_is_not_tracked(hass, entry, device):
    device.ws_fail_with = "Write failed - disk full?"
    with pytest.raises(HomeAssistantError) as err:
        await _call(hass, "send_book", entry, file="Dune.epub")
    assert err.value.translation_key == "device_error"
    assert entry.runtime_data.store.all() == []


@pytest.mark.parametrize(
    ("file", "key"),
    [("Missing.epub", "file_not_found"), ("../secret.epub", "invalid_file")],
)
async def test_invalid_book(hass, entry, file, key):
    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, "send_book", entry, file=file)
    assert err.value.translation_key == key


async def test_remove_untracked(hass, entry):
    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, "remove_book", entry, file="Dune.epub")
    assert err.value.translation_key == "not_tracked"


async def test_remove_missing_on_device(hass, entry, device):
    await _call(hass, "send_book", entry, file="Dune.epub")
    del device.files["/Books/Dune.epub"]
    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, "remove_book", entry, file="Dune.epub")
    assert err.value.translation_key == "not_on_device"
    assert entry.runtime_data.store.get("book", "Dune.epub") is not None

    await _call(hass, "remove_book", entry, file="Dune.epub", forget_missing=True)
    assert entry.runtime_data.store.get("book", "Dune.epub") is None


async def test_unknown_entry(hass, entry):
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN,
            "remove_book",
            {"config_entry_id": "nope", "file": "Dune.epub"},
            blocking=True,
        )
    assert err.value.translation_key == "entry_not_found"
