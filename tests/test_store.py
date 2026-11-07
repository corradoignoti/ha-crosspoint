"""Tests for the transfer store."""

from __future__ import annotations

from datetime import UTC, datetime

from homeassistant.core import HomeAssistant

from custom_components.crosspoint.store import TransferStore, sha256_file


async def test_record_persist_forget(hass: HomeAssistant, hass_storage):
    store = TransferStore(hass, "entry1")
    await store.async_load()
    assert store.all() == []
    await store.async_record(
        kind="book",
        file="a.epub",
        sha256="abc",
        size=3,
        sent_at=datetime(2026, 11, 5, tzinfo=UTC),
        device_path="/Books/a.epub",
    )

    reloaded = TransferStore(hass, "entry1")
    await reloaded.async_load()
    transfer = reloaded.get("book", "a.epub")
    assert transfer.device_path == "/Books/a.epub"
    assert transfer.sent_at == "2026-11-05T00:00:00+00:00"
    assert reloaded.get("wallpaper", "a.epub") is None

    await reloaded.async_forget("book", "a.epub")
    assert reloaded.all("book") == []
    assert hass_storage["crosspoint.entry1.transfers"]["data"]["transfers"] == []


def test_sha256_file(tmp_path):
    path = tmp_path / "f"
    path.write_bytes(b"hello")
    assert sha256_file(path) == (
        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )


async def _record(store: TransferStore, file: str = "a.epub") -> None:
    await store.async_record(
        kind="book",
        file=file,
        sha256="abc",
        size=3,
        sent_at=datetime(2026, 11, 5, tzinfo=UTC),
        device_path=f"/Books/{file}",
    )


async def test_transfers_are_tracked_per_device(hass: HomeAssistant, hass_storage):
    store = TransferStore(hass, "entry1")
    await store.async_load()
    now = datetime(2026, 11, 7, tzinfo=UTC)

    await store.async_set_active_device("dev-a", "X4", "10.0.0.2", now)
    await _record(store)
    await store.async_set_active_device("dev-b", "X3", "10.0.0.3", now)
    assert store.get("book", "a.epub") is None
    assert store.all() == []
    await _record(store)

    assert set(store.installed_on("book", "a.epub")) == {"dev-a", "dev-b"}
    await store.async_forget("book", "a.epub")
    assert store.installed_on("book", "a.epub") == ["dev-a"]

    reloaded = TransferStore(hass, "entry1")
    await reloaded.async_load()
    assert reloaded.active_device == "dev-b"
    assert {d.device_id for d in reloaded.devices} == {"dev-a", "dev-b"}
    await reloaded.async_set_active_device("dev-a", "X4", "10.0.0.2", now)
    assert reloaded.get("book", "a.epub").device_id == "dev-a"


async def test_legacy_transfers_go_to_first_identified_device(
    hass: HomeAssistant, hass_storage
):
    store = TransferStore(hass, "entry1")
    await store.async_load()
    await _record(store)  # no device identified yet
    now = datetime(2026, 11, 7, tzinfo=UTC)

    await store.async_set_active_device("dev-a", "X4", None, now)
    assert store.get("book", "a.epub").device_id == "dev-a"
    await store.async_set_active_device("dev-b", "X4", None, now)
    assert store.get("book", "a.epub") is None


async def test_missing_device_id_keeps_selection(hass: HomeAssistant, hass_storage):
    store = TransferStore(hass, "entry1")
    await store.async_load()
    now = datetime(2026, 11, 7, tzinfo=UTC)
    await store.async_set_active_device("dev-a", "X4", None, now)
    await store.async_set_active_device(None, "X4", None, now)
    assert store.active_device == "dev-a"
