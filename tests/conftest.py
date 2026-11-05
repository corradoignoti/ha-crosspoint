"""Shared fixtures for CrossPoint tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.crosspoint.api.device import CrossPointDeviceClient
from custom_components.crosspoint.const import DOMAIN

from .fake_device import FakeCrossPoint


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom_components in every test."""
    return


@pytest.fixture(autouse=True)
def isolated_cache_dir(hass, tmp_path):
    """Keep the Home Assistant cache directory (cover thumbnails) per test."""
    config_dir = tmp_path / "ha_config"
    config_dir.mkdir()
    hass.config.config_dir = str(config_dir)


@pytest.fixture
async def device():
    """A running fake CrossPoint firmware server."""

    fake = FakeCrossPoint()
    await fake.start()
    yield fake
    await fake.close()


@pytest.fixture
def setup_device_entry(hass, device, tmp_path):
    """Return a coroutine that sets up an entry talking to the fake device.

    The library lives in ``tmp_path`` (``books`` and ``wallpapers``
    subfolders); create library files before calling it.
    """

    async def _setup():
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id="crosspoint.local",
            title="CrossPoint",
            data={
                "host": "crosspoint.local",
                "model": "xteink_x4",
                "library_path": str(tmp_path),
                "books_dir": "books",
                "wallpapers_dir": "wallpapers",
            },
        )
        entry.add_to_hass(hass)

        def make_client(session, host, ws_port):
            return CrossPointDeviceClient(
                session,
                "127.0.0.1",
                http_port=device.http.port,
                ws_port=device.ws.port,
            )

        with patch("custom_components.crosspoint.CrossPointDeviceClient", make_client):
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
        return entry

    return _setup
