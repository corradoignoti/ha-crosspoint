"""Tests for setup, reachability coordinator and device entities."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.crosspoint.api.errors import CrossPointConnectionError
from custom_components.crosspoint.const import (
    CONF_BOOKS_DIR,
    CONF_LIBRARY_PATH,
    CONF_MODEL,
    CONF_WALLPAPERS_DIR,
    CONF_WS_PORT,
    DEVICE_POLL_INTERVAL_S,
    DOMAIN,
)

GET_STATUS = "custom_components.crosspoint.api.device.CrossPointDeviceClient.get_status"
ONLINE = "binary_sensor.xteink_x4_online"
RSSI = "sensor.xteink_x4_wi_fi_signal"
STATUS = {"version": "1.2.3", "device": "X4", "rssi": -55}
OFFLINE = CrossPointConnectionError("offline")


@pytest.fixture(autouse=True)
def no_reconcile():
    """These tests only fake the status probe: skip the device file listing."""
    with patch("custom_components.crosspoint.async_reconcile_device", AsyncMock()):
        yield


@pytest.fixture
def entry(hass: HomeAssistant, tmp_path) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="crosspoint.local",
        data={
            "host": "crosspoint.local",
            CONF_MODEL: "xteink_x4",
            CONF_WS_PORT: 81,
            CONF_LIBRARY_PATH: str(tmp_path),
            CONF_BOOKS_DIR: "books",
            CONF_WALLPAPERS_DIR: "wallpapers",
        },
    )
    entry.add_to_hass(hass)
    return entry


async def _setup(hass: HomeAssistant, entry: MockConfigEntry, get_status: AsyncMock):
    with patch(GET_STATUS, get_status):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


async def _tick(hass: HomeAssistant) -> None:
    async_fire_time_changed(
        hass, dt_util.utcnow() + timedelta(seconds=DEVICE_POLL_INTERVAL_S + 1)
    )
    await hass.async_block_till_done()


async def test_setup_offline(hass: HomeAssistant, entry):
    await _setup(hass, entry, AsyncMock(side_effect=OFFLINE))
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get(ONLINE).state == STATE_OFF


async def test_setup_online_updates_device(hass: HomeAssistant, entry):
    await _setup(hass, entry, AsyncMock(return_value=STATUS))
    assert hass.states.get(ONLINE).state == STATE_ON
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, entry.entry_id), entry.entry_id
    )
    assert device.sw_version == "1.2.3"
    assert device.model == "Xteink X4"
    rssi = er.async_get(hass).async_get(RSSI)
    assert rssi.disabled_by is er.RegistryEntryDisabler.INTEGRATION


async def test_online_offline_transitions(hass: HomeAssistant, entry):
    get_status = AsyncMock(side_effect=OFFLINE)
    with patch(GET_STATUS, get_status):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert hass.states.get(ONLINE).state == STATE_OFF

        get_status.side_effect = None
        get_status.return_value = STATUS
        await _tick(hass)
        assert hass.states.get(ONLINE).state == STATE_ON

        get_status.side_effect = OFFLINE
        await _tick(hass)
        assert hass.states.get(ONLINE).state == STATE_OFF


async def test_rssi_unavailable_when_offline(hass: HomeAssistant, entry):
    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_rssi",
        suggested_object_id="xteink_x4_wi_fi_signal",
        disabled_by=None,
    )
    get_status = AsyncMock(return_value=STATUS)
    with patch(GET_STATUS, get_status):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert hass.states.get(RSSI).state == "-55"
        get_status.side_effect = OFFLINE
        await _tick(hass)
        assert hass.states.get(RSSI).state == STATE_UNAVAILABLE


async def test_ensure_online(hass: HomeAssistant, entry):
    get_status = AsyncMock(return_value=STATUS)
    with patch(GET_STATUS, get_status):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        coordinator = entry.runtime_data.coordinator

        await coordinator.async_ensure_online()

        get_status.side_effect = OFFLINE
        with pytest.raises(HomeAssistantError) as err:
            await coordinator.async_ensure_online()
        assert err.value.translation_key == "device_offline"
        await hass.async_block_till_done()
        # The live probe also refreshes the entity right away.
        assert hass.states.get(ONLINE).state == STATE_OFF


async def test_connection_lost_marks_offline(hass: HomeAssistant, entry):
    await _setup(hass, entry, AsyncMock(return_value=STATUS))
    entry.runtime_data.coordinator.async_mark_connection_lost(OFFLINE)
    await hass.async_block_till_done()
    assert hass.states.get(ONLINE).state == STATE_OFF


async def test_unload(hass: HomeAssistant, entry):
    await _setup(hass, entry, AsyncMock(return_value=STATUS))
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_connected_reader_is_identified(hass: HomeAssistant, entry):
    get_status = AsyncMock(
        return_value={**STATUS, "deviceId": "dev-a", "ip": "1.2.3.4"}
    )
    await _setup(hass, entry, get_status)
    store = entry.runtime_data.store
    assert store.active_device == "dev-a"
    assert [d.device_id for d in store.devices] == ["dev-a"]
    get_status.assert_called_with(plugin="home-assistant-crosspoint")

    # Another unit shows up behind the same address.
    get_status.return_value = {**STATUS, "deviceId": "dev-b"}
    with patch(GET_STATUS, get_status):
        await _tick(hass)
    assert store.active_device == "dev-b"
    assert {d.device_id for d in store.devices} == {"dev-a", "dev-b"}


async def test_reader_found_again_at_another_address(
    hass: HomeAssistant, entry, no_discovery
):
    """A reader answering on a new IP is found by discovery and identified."""
    from custom_components.crosspoint.discovery import DiscoveredDevice

    new_ip = "192.168.1.77"
    no_discovery.return_value = [DiscoveredDevice(new_ip, "crosspoint", 81)]
    client_hosts: list[str] = []

    async def get_status(self, plugin=None):
        client_hosts.append(self.host)
        if self.host != new_ip:
            raise OFFLINE
        return {**STATUS, "deviceId": "dev-b", "ip": new_ip}

    with patch(GET_STATUS, get_status):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    runtime = entry.runtime_data
    assert runtime.coordinator.online
    assert runtime.client.host == new_ip
    assert runtime.store.active_device == "dev-b"
    assert client_hosts[0] != new_ip


async def test_rediscovery_is_throttled(hass: HomeAssistant, entry, no_discovery):
    await _setup(hass, entry, AsyncMock(side_effect=OFFLINE))
    assert no_discovery.call_count == 1
    with patch(GET_STATUS, AsyncMock(side_effect=OFFLINE)):
        await _tick(hass)
    assert no_discovery.call_count == 1


async def test_serial_is_the_fallback_reader_id(hass: HomeAssistant, entry):
    await _setup(hass, entry, AsyncMock(return_value={**STATUS, "serial": "X4BW02"}))
    assert entry.runtime_data.store.active_device == "serial:X4BW02"


async def test_model_follows_the_connected_reader(hass: HomeAssistant, tmp_path):
    """An entry configured as Cross-Share shows an X4 when an X4 is connected."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="192.168.188.66",
        data={
            "host": "192.168.188.66",
            CONF_MODEL: "cross_share",
            CONF_WS_PORT: 81,
            CONF_LIBRARY_PATH: str(tmp_path),
            CONF_BOOKS_DIR: "books",
            CONF_WALLPAPERS_DIR: "wallpapers",
        },
    )
    entry.add_to_hass(hass)
    status = {**STATUS, "device": "xteink_x4_classic", "deviceId": "dev-a"}
    get_status = AsyncMock(return_value=status)
    await _setup(hass, entry, get_status)

    assert entry.runtime_data.model.key == "xteink_x4"
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, entry.entry_id), entry.entry_id
    )
    assert device.model == "Xteink X4"
    assert device.name == "Xteink X4"

    # Offline, the last known model of the active reader is kept.
    get_status.side_effect = OFFLINE
    with patch(GET_STATUS, get_status):
        await _tick(hass)
    assert not entry.runtime_data.coordinator.online
    assert entry.runtime_data.model.key == "xteink_x4"
