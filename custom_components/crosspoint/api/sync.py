"""Async client for the CrossPoint Sync (KOSync-compatible) server."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import aiohttp

from .errors import CrossPointConnectionError, CrossPointError, CrossPointResponseError

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)


class CrossPointSyncAuthError(CrossPointError):
    """The server rejected the credentials."""


class CrossPointSyncRateLimitError(CrossPointError):
    """The server is rate limiting this client (often after auth failures)."""


def password_key(password: str) -> str:
    """Return the KOSync key for a password: lowercase hex MD5."""
    # MD5 is mandated by the KOSync protocol; it is not used for security here.
    return hashlib.md5(password.encode("utf-8"), usedforsecurity=False).hexdigest()


def normalize_url(url: str) -> str:
    """Return the server base URL without a trailing slash."""
    return url.strip().rstrip("/")


class CrossPointSyncClient:
    """Read reading statistics of one CrossPoint Sync user."""

    def __init__(
        self, session: aiohttp.ClientSession, url: str, username: str, key: str
    ) -> None:
        self._session = session
        self.url = normalize_url(url)
        self.username = username
        self._headers = {
            "x-auth-user": username,
            "x-auth-key": key,
            "Accept": "application/json",
        }

    async def _get(self, path: str, **params: Any) -> Any:
        try:
            async with self._session.get(
                f"{self.url}{path}",
                headers=self._headers,
                params=params or None,
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                text = await resp.text()
                if resp.status == 401:
                    raise CrossPointSyncAuthError("Invalid credentials")
                if resp.status == 429:
                    raise CrossPointSyncRateLimitError("Too many requests")
                if resp.status >= 400:
                    raise CrossPointResponseError(
                        text.strip()[:200] or resp.reason or "Request failed",
                        status=resp.status,
                    )
        except (aiohttp.ClientConnectionError, TimeoutError) as err:
            raise CrossPointConnectionError(f"Cannot reach {self.url}: {err}") from err
        except aiohttp.ClientError as err:
            raise CrossPointResponseError(str(err)) from err
        try:
            return json.loads(text)
        except ValueError as err:
            raise CrossPointResponseError("Invalid JSON response") from err

    async def async_authorize(self) -> None:
        """Validate the credentials; raise CrossPointSyncAuthError if wrong."""
        data = await self._get("/users/auth")
        if not isinstance(data, dict) or data.get("authorized") != "OK":
            raise CrossPointSyncAuthError("Invalid credentials")

    async def async_summary(self) -> dict[str, Any]:
        """Return the combined statistics across devices."""
        data = await self._get("/api/v1/stats/summary")
        if not isinstance(data, dict):
            raise CrossPointResponseError("Invalid summary response")
        return data

    async def async_global(self) -> dict[str, Any]:
        """Return the per-device statistics snapshots."""
        data = await self._get("/api/v1/stats/global")
        if not isinstance(data, dict):
            raise CrossPointResponseError("Invalid stats response")
        return data
