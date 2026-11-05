"""Tests for the CrossPoint Sync client."""

from __future__ import annotations

import aiohttp
import pytest

from custom_components.crosspoint.api.sync import (
    CrossPointSyncAuthError,
    CrossPointSyncClient,
    CrossPointSyncRateLimitError,
    password_key,
)

from .fake_sync import FakeSync

pytestmark = pytest.mark.usefixtures("socket_enabled")


@pytest.fixture
async def sync():
    fake = FakeSync()
    await fake.server.start_server()
    yield fake
    await fake.server.close()


def test_password_key():
    assert password_key("secret") == "5ebe2294ecd0e0f08eab7690d2a6ee69"


async def test_client(sync):
    async with aiohttp.ClientSession() as session:
        good = CrossPointSyncClient(
            session, sync.url + "/", "alice", password_key("secret")
        )
        await good.async_authorize()
        assert (await good.async_summary())["pages"] == 9500

        bad = CrossPointSyncClient(session, sync.url, "alice", password_key("wrong"))
        with pytest.raises(CrossPointSyncAuthError):
            await bad.async_authorize()

        sync.fail_status = 429
        with pytest.raises(CrossPointSyncRateLimitError):
            await good.async_summary()
