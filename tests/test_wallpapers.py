"""End-to-end tests of wallpaper operations against the fake firmware server."""

from __future__ import annotations

import io

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from PIL import Image

from custom_components.crosspoint.const import DOMAIN

pytestmark = pytest.mark.usefixtures("socket_enabled")


def _save(path, img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    path.write_bytes(buf.getvalue())


@pytest.fixture
def wallpapers(tmp_path):
    root = tmp_path / "wallpapers"
    root.mkdir()
    _save(root / "sea.png", Image.new("RGB", (1200, 900), (30, 90, 160)))
    overlay = Image.new("RGBA", (600, 1000), (0, 0, 0, 0))
    overlay.paste((0, 0, 0, 255), (50, 50, 550, 300))
    _save(root / "clock overlay.png", overlay)
    (root / "broken.png").write_bytes(b"not an image")
    return root


@pytest.fixture
async def entry(setup_device_entry, wallpapers):
    return await setup_device_entry()


async def _send(hass, entry, file, **data):
    return await hass.services.async_call(
        DOMAIN,
        "send_wallpaper",
        {"config_entry_id": entry.entry_id, "file": file, **data},
        blocking=True,
        return_response=True,
    )


def _image(device, path) -> Image.Image:
    img = Image.open(io.BytesIO(device.files[path]))
    img.load()
    return img


def _status(entry, file):
    items = entry.runtime_data.library.items("wallpaper")
    return next(i.status for i in items if i.file == file)


async def test_send_normal(hass: HomeAssistant, entry, device):
    response = await _send(hass, entry, "sea.png")
    path = response["device_path"]
    assert path.startswith("/sleep/sea-") and path.endswith(".bmp")
    img = _image(device, path)
    assert (img.format, img.mode, img.size) == ("BMP", "RGB", (480, 800))
    tracked = entry.runtime_data.store.get("wallpaper", "sea.png")
    assert tracked.mode == "normal"
    assert _status(entry, "sea.png") == "installed"


async def test_transparent_needs_transparency(hass: HomeAssistant, entry, device):
    with pytest.raises(ServiceValidationError) as err:
        await _send(hass, entry, "sea.png", mode="transparent")
    assert err.value.translation_key == "no_transparency"
    assert device.files == {}

    response = await _send(hass, entry, "sea.png", mode="transparent", force=True)
    assert response["device_path"].startswith("/sleep-overlay/")
    assert response["has_transparency"] is False


async def test_transparent_overlay(hass: HomeAssistant, entry, device):
    response = await _send(hass, entry, "clock overlay.png", mode="transparent")
    path = response["device_path"]
    assert path.startswith("/sleep-overlay/clock_overlay-") and path.endswith(".png")
    assert response["has_transparency"] is True
    img = _image(device, path)
    assert (img.mode, img.size) == ("RGBA", (480, 800))
    assert img.getchannel("A").getextrema()[0] == 0


async def test_switch_mode_replaces_previous_file(hass, entry, device):
    first = await _send(hass, entry, "clock overlay.png", mode="transparent")
    again = await _send(hass, entry, "clock overlay.png", mode="transparent")
    assert again["device_path"] == first["device_path"]  # overwritten in place
    second = await _send(hass, entry, "clock overlay.png", mode="normal")
    assert first["device_path"] not in device.files
    assert second["device_path"] in device.files
    assert len(entry.runtime_data.store.all("wallpaper")) == 1


async def test_remove_wallpaper(hass, entry, device):
    response = await _send(hass, entry, "sea.png")
    await hass.services.async_call(
        DOMAIN,
        "remove_wallpaper",
        {"config_entry_id": entry.entry_id, "file": "sea.png"},
        blocking=True,
    )
    assert response["device_path"] not in device.files
    assert entry.runtime_data.store.all("wallpaper") == []


async def test_invalid_image(hass, entry):
    with pytest.raises(ServiceValidationError) as err:
        await _send(hass, entry, "broken.png")
    assert err.value.translation_key == "invalid_image"


async def test_offline(hass, entry, device):
    await device.close()
    with pytest.raises(HomeAssistantError) as err:
        await _send(hass, entry, "sea.png")
    assert err.value.translation_key == "device_offline"


async def test_check_does_not_need_device(hass, entry, device):
    await device.close()
    wallpapers = entry.runtime_data.wallpapers
    assert await wallpapers.async_check("clock overlay.png") is True
    assert await wallpapers.async_check("sea.png") is False
