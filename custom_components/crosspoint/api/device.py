"""Async client for the CrossPoint firmware web server.

Only features exposed by the stock CrossPoint web server are used:
HTTP on port 80 (status, listing, upload, delete, mkdir) and the binary
WebSocket upload protocol on port 81. The server has no authentication.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import posixpath
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import aiohttp

from ..const import DEFAULT_HTTP_PORT, DEFAULT_WS_PORT
from .errors import CrossPointConnectionError, CrossPointResponseError

STATUS_TIMEOUT = aiohttp.ClientTimeout(total=5)
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)
# Uploads can be long on a slow ESP32 link: bound inactivity, not total time.
UPLOAD_TIMEOUT = aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=60)
WS_CHUNK_SIZE = 4096
WS_REPLY_TIMEOUT = 30.0

ProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True, slots=True)
class DeviceFile:
    """An entry returned by the device file listing."""

    name: str
    size: int
    is_directory: bool
    is_epub: bool


def _validate_name(filename: str) -> None:
    """Reject file names the firmware protocols cannot carry safely."""
    if not filename or "/" in filename or ":" in filename or filename in (".", ".."):
        raise ValueError(f"Invalid file name for the device: {filename!r}")


def _normalize_dir(path: str) -> str:
    """Return an absolute device directory path without a trailing slash."""
    normalized = posixpath.normpath("/" + path.strip("/"))
    return "/" if normalized in ("/", "//") else normalized


class CrossPointDeviceClient:
    """Talk to one CrossPoint e-reader over Wi-Fi."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        *,
        http_port: int = DEFAULT_HTTP_PORT,
        ws_port: int = DEFAULT_WS_PORT,
    ) -> None:
        self._session = session
        self._http_port = http_port
        self.set_address(host, ws_port)
        # The firmware accepts a single upload at a time.
        self._upload_lock = asyncio.Lock()

    def set_address(self, host: str, ws_port: int = DEFAULT_WS_PORT) -> None:
        """Point the client at another address (e.g. a reader found again)."""
        self.host = host
        self.ws_port = ws_port
        self._base_url = f"http://{host}:{self._http_port}"
        self._ws_url = f"ws://{host}:{ws_port}/"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        timeout: aiohttp.ClientTimeout = REQUEST_TIMEOUT,
        **kwargs: Any,
    ) -> str:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.request(
                method, url, timeout=timeout, **kwargs
            ) as resp:
                text = await resp.text()
                if resp.status >= 400:
                    raise CrossPointResponseError(
                        text.strip() or resp.reason or "Request failed",
                        status=resp.status,
                    )
                return text
        except (aiohttp.ClientConnectionError, TimeoutError) as err:
            raise CrossPointConnectionError(
                f"Cannot reach CrossPoint at {self.host}: {err}"
            ) from err
        except aiohttp.ClientError as err:
            raise CrossPointResponseError(str(err)) from err

    async def get_status(self, plugin: str | None = None) -> dict[str, Any]:
        """Return the device status; raises CrossPointConnectionError if offline.

        With ``plugin`` the firmware also returns ``deviceId``, a stable
        identifier of the unit (derived per plugin name).
        """
        text = await self._request(
            "GET",
            "/api/status",
            timeout=STATUS_TIMEOUT,
            params={"plugin": plugin} if plugin else None,
        )
        try:
            data = json.loads(text)
        except ValueError as err:
            raise CrossPointResponseError("Invalid status response") from err
        if not isinstance(data, dict):
            raise CrossPointResponseError("Invalid status response")
        return data

    async def list_files(self, path: str = "/") -> list[DeviceFile]:
        """List a directory on the SD card."""
        text = await self._request(
            "GET", "/api/files", params={"path": _normalize_dir(path)}
        )
        try:
            entries = json.loads(text)
        except ValueError as err:
            raise CrossPointResponseError("Invalid file listing") from err
        return [
            DeviceFile(
                name=str(entry.get("name", "")),
                size=int(entry.get("size", 0)),
                is_directory=bool(entry.get("isDirectory", False)),
                is_epub=bool(entry.get("isEpub", False)),
            )
            for entry in entries
            if isinstance(entry, dict)
        ]

    async def mkdir(self, parent: str, name: str) -> None:
        """Create folder ``name`` inside ``parent``."""
        _validate_name(name)
        await self._request(
            "POST", "/mkdir", data={"name": name, "path": _normalize_dir(parent)}
        )

    async def ensure_dir(self, path: str) -> None:
        """Create every missing component of an absolute directory path."""
        current = "/"
        for part in [p for p in _normalize_dir(path).split("/") if p]:
            existing = {
                f.name for f in await self.list_files(current) if f.is_directory
            }
            if part not in existing:
                # Dot-folders (e.g. /.sleep) are hidden from listings, so the
                # folder may already exist; a real failure surfaces on upload.
                with contextlib.suppress(CrossPointResponseError):
                    await self.mkdir(current, part)
            current = posixpath.join(current, part)

    async def delete(self, path: str) -> None:
        """Delete a file (or an empty folder) on the SD card."""
        await self._request("POST", "/delete", data={"path": path})

    async def upload(
        self,
        data: bytes,
        dest_dir: str,
        filename: str,
        *,
        overwrite: bool = False,
        progress: ProgressCallback | None = None,
    ) -> str:
        """Upload ``data`` and return the full path of the file on the device.

        The fast WebSocket protocol is preferred. It never overwrites, so
        overwrites go through HTTP. If the WebSocket server cannot be reached
        at all, the upload falls back to HTTP.
        """
        _validate_name(filename)
        dest_dir = _normalize_dir(dest_dir)
        async with self._upload_lock:
            if not overwrite:
                try:
                    await self._upload_ws(data, dest_dir, filename, progress)
                except _WebSocketUnavailable:
                    await self._upload_http(data, dest_dir, filename, False)
            else:
                await self._upload_http(data, dest_dir, filename, True)
        if progress:
            progress(len(data), len(data))
        return posixpath.join(dest_dir, filename)

    async def _upload_http(
        self, data: bytes, dest_dir: str, filename: str, overwrite: bool
    ) -> None:
        form = aiohttp.FormData()
        form.add_field(
            "file", data, filename=filename, content_type="application/octet-stream"
        )
        params = {"path": dest_dir}
        if overwrite:
            params["overwrite"] = "1"
        await self._request(
            "POST", "/upload", params=params, data=form, timeout=UPLOAD_TIMEOUT
        )

    async def _upload_ws(
        self,
        data: bytes,
        dest_dir: str,
        filename: str,
        progress: ProgressCallback | None,
    ) -> None:
        try:
            ws = await self._session.ws_connect(
                self._ws_url, timeout=aiohttp.ClientWSTimeout(ws_close=10)
            )
        except (aiohttp.ClientError, TimeoutError) as err:
            raise _WebSocketUnavailable from err

        try:
            async with ws:
                await ws.send_str(f"START:{filename}:{len(data)}:{dest_dir}")
                reply = await self._ws_receive_text(ws)
                if reply != "READY":
                    raise _ws_error(reply)

                outcome: asyncio.Future[None] = (
                    asyncio.get_running_loop().create_future()
                )
                reader = asyncio.create_task(
                    self._ws_read_until_done(ws, outcome, progress)
                )
                try:
                    view = memoryview(data)
                    for offset in range(0, len(data), WS_CHUNK_SIZE):
                        if outcome.done():
                            break
                        await ws.send_bytes(
                            bytes(view[offset : offset + WS_CHUNK_SIZE])
                        )
                    await asyncio.wait_for(asyncio.shield(outcome), WS_REPLY_TIMEOUT)
                finally:
                    reader.cancel()
        except (aiohttp.ClientError, ConnectionResetError, TimeoutError) as err:
            raise CrossPointConnectionError(
                f"Upload to {self.host} interrupted: {err}"
            ) from err

    async def _ws_read_until_done(
        self,
        ws: aiohttp.ClientWebSocketResponse,
        outcome: asyncio.Future[None],
        progress: ProgressCallback | None,
    ) -> None:
        try:
            while True:
                text = await self._ws_receive_text(ws, timeout=None)
                if text == "DONE":
                    outcome.set_result(None)
                    return
                if text.startswith("PROGRESS:"):
                    if progress:
                        _, received, total = text.split(":", 2)
                        progress(int(received), int(total))
                    continue
                outcome.set_exception(_ws_error(text))
                return
        except Exception as err:
            if not outcome.done():
                outcome.set_exception(err)

    @staticmethod
    async def _ws_receive_text(
        ws: aiohttp.ClientWebSocketResponse, timeout: float | None = WS_REPLY_TIMEOUT
    ) -> str:
        msg = await ws.receive(timeout=timeout)
        if msg.type is aiohttp.WSMsgType.TEXT:
            return str(msg.data).strip()
        if msg.type in (
            aiohttp.WSMsgType.CLOSE,
            aiohttp.WSMsgType.CLOSED,
            aiohttp.WSMsgType.CLOSING,
            aiohttp.WSMsgType.ERROR,
        ):
            raise CrossPointConnectionError("WebSocket closed by the device")
        raise CrossPointResponseError(f"Unexpected WebSocket message: {msg.type}")


class _WebSocketUnavailable(Exception):
    """The WebSocket upload server could not be reached."""


def _ws_error(reply: str) -> CrossPointResponseError:
    message = reply.removeprefix("ERROR:").strip() or "Upload failed"
    return CrossPointResponseError(message)
