"""Tests for reading statistics: sync client, subentry flow, sensors."""

from __future__ import annotations

import pytest
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir

from custom_components.crosspoint.api.sync import password_key
from custom_components.crosspoint.const import DOMAIN
from custom_components.crosspoint.stats import ReadingStats

from .fake_sync import SUMMARY, FakeSync

pytestmark = pytest.mark.usefixtures("socket_enabled")

PREFIX = "sensor.crosspoint_sync_alice"


@pytest.fixture
async def sync():
    fake = FakeSync()
    await fake.server.start_server()
    yield fake
    await fake.server.close()


def _subentry(sync: FakeSync, password: str = "secret") -> ConfigSubentryData:
    return ConfigSubentryData(
        subentry_type="sync_user",
        title="alice",
        unique_id=f"{sync.url}|alice",
        data={"url": sync.url, "username": "alice", "key": password_key(password)},
    )


def test_stats_from_summary():
    stats = ReadingStats.from_summary(SUMMARY)
    assert (stats.seconds, stats.pages, stats.completed, stats.sessions) == (
        190300,
        9500,
        15,
        402,
    )
    assert (stats.current_streak, stats.longest_streak) == (6, 21)
    assert stats.weekday_minutes["sun"] == round(83300 / 60)
    assert stats.time_of_day_minutes["afternoon"] == 1400
    assert stats.last_upload.timestamp() == 1752345678
    empty = ReadingStats.from_summary({"tod": [1], "devices": None})
    assert empty.seconds == 0
    assert empty.time_of_day_minutes == {}
    assert empty.last_upload is None


async def test_sensors(hass: HomeAssistant, setup_device_entry, sync):
    entry = await setup_device_entry(subentries=[_subentry(sync)])
    reading = hass.states.get(f"{PREFIX}_reading_time")
    assert float(reading.state) == pytest.approx(190300 / 3600, abs=0.01)
    assert reading.attributes["unit_of_measurement"] == "h"
    assert reading.attributes["weekday_minutes"]["sat"] == 1000
    assert hass.states.get(f"{PREFIX}_books_finished").state == "15"
    assert hass.states.get(f"{PREFIX}_pages_read").state == "9500"
    assert hass.states.get(f"{PREFIX}_reading_sessions").state == "402"
    assert hass.states.get(f"{PREFIX}_current_streak").state == "6"
    assert hass.states.get(f"{PREFIX}_longest_streak").state == "21"
    last = hass.states.get(f"{PREFIX}_last_upload")
    assert last.state.startswith("2025-07-12T")
    assert last.attributes["devices"] == ["CrossInk", "X3"]

    sync.summary["completed"] = 16
    await hass.services.async_call(
        DOMAIN,
        "refresh_reading_stats",
        {"config_entry_id": entry.entry_id},
        blocking=True,
    )
    assert hass.states.get(f"{PREFIX}_books_finished").state == "16"


async def test_auth_failure_does_not_block_device(
    hass: HomeAssistant, setup_device_entry, sync
):
    entry = await setup_device_entry(subentries=[_subentry(sync, "old password")])
    assert hass.states.get(f"{PREFIX}_reading_time").state == STATE_UNAVAILABLE
    assert hass.states.get("binary_sensor.xteink_x4_online").state == "on"
    [subentry_id] = entry.subentries
    issue = ir.async_get(hass).async_get_issue(
        DOMAIN, f"sync_auth_failed_{subentry_id}"
    )
    assert issue.translation_key == "sync_auth_failed"

    # Fix the password through the subentry reconfigure flow.
    result = await entry.start_subentry_reconfigure_flow(hass, subentry_id)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"url": sync.url, "password": "secret"}
    )
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert hass.states.get(f"{PREFIX}_books_finished").state == "15"
    assert (
        ir.async_get(hass).async_get_issue(DOMAIN, f"sync_auth_failed_{subentry_id}")
        is None
    )


async def test_add_user_flow(hass: HomeAssistant, setup_device_entry, sync):
    entry = await setup_device_entry()
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "sync_user"), context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM
    user = {"url": sync.url + "/", "username": "alice"}

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {**user, "password": "wrong"}
    )
    assert result["errors"] == {"base": "invalid_auth"}

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {**user, "password": "secret"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "url": sync.url,
        "username": "alice",
        "key": password_key("secret"),
    }
    assert "secret" not in str(entry.subentries)
    await hass.async_block_till_done()
    assert hass.states.get(f"{PREFIX}_books_finished").state == "15"

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "sync_user"), context={"source": "user"}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {**user, "password": "secret"}
    )
    assert result["reason"] == "already_configured"


async def test_unreachable_server(hass: HomeAssistant, setup_device_entry):
    result_entry = await setup_device_entry()
    result = await hass.config_entries.subentries.async_init(
        (result_entry.entry_id, "sync_user"), context={"source": "user"}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {"url": "http://127.0.0.1:1", "username": "alice", "password": "x"},
    )
    assert result["errors"] == {"base": "cannot_connect_sync"}
