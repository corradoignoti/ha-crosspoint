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
    assert hass_storage["crosspoint.entry1.transfers"]["data"] == {"transfers": []}


def test_sha256_file(tmp_path):
    path = tmp_path / "f"
    path.write_bytes(b"hello")
    assert sha256_file(path) == (
        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )
