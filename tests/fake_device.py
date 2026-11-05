"""In-process fake of the CrossPoint firmware web server, for tests."""

from __future__ import annotations

import json
import posixpath

from aiohttp import WSMsgType, web
from aiohttp.test_utils import TestServer


class FakeCrossPoint:
    """Implement the subset of the firmware HTTP and WebSocket API we use."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.dirs: set[str] = {"/"}
        self.status = {"version": "1.0.0", "device": "X4", "mode": "STA"}
        self.ws_fail_with: str | None = None
        http = web.Application()
        http.router.add_get("/api/status", self._status)
        http.router.add_get("/api/files", self._files)
        http.router.add_post("/upload", self._upload)
        http.router.add_post("/mkdir", self._mkdir)
        http.router.add_post("/delete", self._delete)
        ws = web.Application()
        ws.router.add_get("/", self._ws)
        self.http = TestServer(http)
        self.ws = TestServer(ws)

    async def start(self) -> None:
        await self.http.start_server()
        await self.ws.start_server()

    async def close(self) -> None:
        await self.http.close()
        await self.ws.close()

    async def _status(self, request: web.Request) -> web.Response:
        return web.json_response(self.status)

    async def _files(self, request: web.Request) -> web.Response:
        path = request.query.get("path", "/")
        entries = [
            {"name": posixpath.basename(d), "size": 0, "isDirectory": True}
            for d in self.dirs
            if d != "/" and posixpath.dirname(d) == path
        ] + [
            {
                "name": posixpath.basename(f),
                "size": len(data),
                "isDirectory": False,
                "isEpub": f.endswith(".epub"),
            }
            for f, data in self.files.items()
            if posixpath.dirname(f) == path
        ]
        return web.Response(text=json.dumps(entries))

    async def _upload(self, request: web.Request) -> web.Response:
        path = request.query.get("path", "/")
        overwrite = request.query.get("overwrite") in ("1", "true")
        form = await request.post()
        field = form["file"]
        target = posixpath.join(path, field.filename)
        if target in self.files and not overwrite:
            return web.Response(status=400, text="File already exists")
        self.files[target] = field.file.read()
        return web.Response(text=f"File uploaded successfully: {field.filename}")

    async def _mkdir(self, request: web.Request) -> web.Response:
        form = await request.post()
        self.dirs.add(posixpath.join(form.get("path", "/"), form["name"]))
        return web.Response(text="Folder created")

    async def _delete(self, request: web.Request) -> web.Response:
        form = await request.post()
        path = form["path"]
        if path not in self.files:
            return web.Response(status=404, text="Not found")
        del self.files[path]
        return web.Response(text="Deleted")

    async def _ws(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        msg = await ws.receive()
        _, name, size, path = msg.data.split(":", 3)
        target = posixpath.join(path, name)
        if target in self.files:
            await ws.send_str(f"ERROR:File already exists: {name}")
            return ws
        await ws.send_str("READY")
        total, buf = int(size), bytearray()
        async for msg in ws:
            if msg.type is not WSMsgType.BINARY:
                break
            buf += msg.data
            if self.ws_fail_with:
                await ws.send_str(f"ERROR:{self.ws_fail_with}")
                return ws
            if len(buf) >= total:
                await ws.send_str(f"PROGRESS:{len(buf)}:{total}")
                self.files[target] = bytes(buf)
                await ws.send_str("DONE")
                break
        return ws
