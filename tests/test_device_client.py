"""Tests for the CrossPoint device client."""

from __future__ import annotations

import aiohttp
import pytest

from custom_components.crosspoint.api.device import CrossPointDeviceClient
from custom_components.crosspoint.api.errors import (
    CrossPointConnectionError,
    CrossPointResponseError,
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
async def client(device):
    async with aiohttp.ClientSession() as session:
        yield CrossPointDeviceClient(
            session,
            "127.0.0.1",
            http_port=device.http.port,
            ws_port=device.ws.port,
        )


async def test_status(client, device):
    assert (await client.get_status())["version"] == "1.0.0"


async def test_offline_raises_connection_error():
    async with aiohttp.ClientSession() as session:
        client = CrossPointDeviceClient(session, "127.0.0.1", http_port=1)
        with pytest.raises(CrossPointConnectionError):
            await client.get_status()


async def test_websocket_upload_with_progress(client, device):
    data = b"x" * 10_000
    seen: list[tuple[int, int]] = []
    path = await client.upload(
        data, "/Books", "a.epub", progress=lambda r, t: seen.append((r, t))
    )
    assert path == "/Books/a.epub"
    assert device.files["/Books/a.epub"] == data
    assert seen[-1] == (10_000, 10_000)


async def test_websocket_error_is_reported(client, device):
    device.ws_fail_with = "Write failed - disk full?"
    with pytest.raises(CrossPointResponseError, match="disk full"):
        await client.upload(b"x" * 10_000, "/", "a.epub")


async def test_overwrite_uses_http(client, device):
    device.files["/a.epub"] = b"old"
    await client.upload(b"new", "/", "a.epub", overwrite=True)
    assert device.files["/a.epub"] == b"new"


async def test_falls_back_to_http_without_websocket(device):
    async with aiohttp.ClientSession() as session:
        client = CrossPointDeviceClient(
            session, "127.0.0.1", http_port=device.http.port, ws_port=1
        )
        await client.upload(b"data", "/", "b.epub")
    assert device.files["/b.epub"] == b"data"


async def test_list_delete_and_ensure_dir(client, device):
    await client.ensure_dir("/Books/Sci-Fi")
    assert {"/Books", "/Books/Sci-Fi"} <= device.dirs
    await client.upload(b"data", "/Books", "c.epub")
    files = await client.list_files("/Books")
    assert {f.name for f in files} == {"Sci-Fi", "c.epub"}
    await client.delete("/Books/c.epub")
    assert "/Books/c.epub" not in device.files
    with pytest.raises(CrossPointResponseError) as err:
        await client.delete("/Books/c.epub")
    assert err.value.status == 404


@pytest.mark.parametrize("name", ["", "a/b.epub", "a:b.epub", ".."])
async def test_invalid_file_names(client, name):
    with pytest.raises(ValueError):
        await client.upload(b"x", "/", name)
