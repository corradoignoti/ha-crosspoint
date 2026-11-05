"""Tests for the CrossPoint config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.crosspoint.const import (
    CONF_BOOKS_DIR,
    CONF_DEVICE_BOOKS_DIR,
    CONF_LIBRARY_PATH,
    CONF_MODEL,
    CONF_SCAN_INTERVAL,
    CONF_WALLPAPERS_DIR,
    CONF_WS_PORT,
    DOMAIN,
)
from custom_components.crosspoint.discovery import DiscoveredDevice

FLOW = "custom_components.crosspoint.config_flow"


@pytest.fixture
def library(hass: HomeAssistant, tmp_path):
    hass.config.allowlist_external_dirs = {str(tmp_path)}
    return tmp_path


@pytest.fixture(autouse=True)
def mock_setup_entry():
    """Do not set up the created entry: these tests cover the flow only."""
    with patch(
        "custom_components.crosspoint.async_setup_entry", AsyncMock(return_value=True)
    ) as mock:
        yield mock


def _patch(discovered=(), status=None):
    return (
        patch(f"{FLOW}.async_discover", AsyncMock(return_value=list(discovered))),
        patch(f"{FLOW}._async_probe", AsyncMock(return_value=status)),
    )


def _library_input(path):
    return {
        CONF_LIBRARY_PATH: str(path),
        CONF_BOOKS_DIR: "books",
        CONF_WALLPAPERS_DIR: "/wallpapers/",
    }


async def test_manual_flow_online(hass: HomeAssistant, library):
    p1, p2 = _patch(status={"device": "X3"})
    with p1, p2:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["step_id"] == "device"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "crosspoint.local", CONF_MODEL: "xteink_x3"}
        )
        assert result["step_id"] == "library"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _library_input(library)
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "host": "crosspoint.local",
        CONF_MODEL: "xteink_x3",
        CONF_WS_PORT: 81,
        CONF_LIBRARY_PATH: str(library),
        CONF_BOOKS_DIR: "books",
        CONF_WALLPAPERS_DIR: "wallpapers",
    }
    assert result["options"] == {
        CONF_SCAN_INTERVAL: 30,
        CONF_DEVICE_BOOKS_DIR: "/Books",
    }
    assert (library / "books").is_dir()
    assert (library / "wallpapers").is_dir()


async def test_offline_device_needs_confirmation(hass: HomeAssistant, library):
    p1, p2 = _patch(status=None)
    with p1, p2:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        user = {"host": "10.0.0.9", CONF_MODEL: "xteink_x4"}
        result = await hass.config_entries.flow.async_configure(result["flow_id"], user)
        assert result["errors"] == {"base": "cannot_connect_confirm"}
        result = await hass.config_entries.flow.async_configure(result["flow_id"], user)
    assert result["step_id"] == "library"


async def test_discovered_device(hass: HomeAssistant, library):
    found = DiscoveredDevice("192.168.1.20", "crosspoint.local", 82)
    p1, p2 = _patch(discovered=[found], status={"device": "Xteink X3"})
    with p1, p2:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["step_id"] == "pick"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "192.168.1.20"}
        )
        assert result["step_id"] == "device"
        schema = {str(k): k.default() for k in result["data_schema"].schema}
        assert schema == {"host": "192.168.1.20", CONF_MODEL: "xteink_x3"}
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], schema
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _library_input(library)
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_WS_PORT] == 82


async def test_library_errors(hass: HomeAssistant, library, tmp_path_factory):
    p1, p2 = _patch(status={})
    with p1, p2:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "crosspoint.local", CONF_MODEL: "xteink_x4"}
        )
        outside = tmp_path_factory.mktemp("outside")
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _library_input(outside)
        )
        assert result["errors"] == {"base": "path_not_allowed"}
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _library_input(library / "missing")
        )
        assert result["errors"] == {"base": "path_not_found"}
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {**_library_input(library), CONF_BOOKS_DIR: "../escape"},
        )
        assert result["errors"] == {"base": "invalid_subfolder"}


async def test_already_configured(hass: HomeAssistant, library):
    MockConfigEntry(
        domain=DOMAIN, unique_id="crosspoint.local", data={"host": "crosspoint.local"}
    ).add_to_hass(hass)
    p1, p2 = _patch(status={})
    with p1, p2:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "CrossPoint.local", CONF_MODEL: "xteink_x4"}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(hass: HomeAssistant, library):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="crosspoint.local",
        data={
            "host": "crosspoint.local",
            CONF_MODEL: "xteink_x4",
            **_library_input(library),
        },
        options={CONF_SCAN_INTERVAL: 30},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 10, CONF_DEVICE_BOOKS_DIR: "../x"}
    )
    assert result["errors"] == {"base": "invalid_device_folder"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 10, CONF_DEVICE_BOOKS_DIR: "ebooks/"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_SCAN_INTERVAL: 10, CONF_DEVICE_BOOKS_DIR: "/ebooks"}


async def test_reconfigure(hass: HomeAssistant, library):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="crosspoint.local",
        data={
            "host": "crosspoint.local",
            CONF_MODEL: "xteink_x4",
            CONF_WS_PORT: 81,
            **_library_input(library),
        },
    )
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"host": "10.0.0.5", CONF_MODEL: "cross_share", **_library_input(library)},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["host"] == "10.0.0.5"
    assert entry.data[CONF_MODEL] == "cross_share"
    assert entry.unique_id == "10.0.0.5"
