"""In-process fake of a CrossPoint Sync server, for tests."""

from __future__ import annotations

import hashlib

from aiohttp import web
from aiohttp.test_utils import TestServer

SUMMARY = {
    "sessions": 402,
    "seconds": 190300,
    "pages": 9500,
    "completed": 15,
    "tod": [1200, 84000, 60100, 45000],
    "dow": [8000, 9000, 7000, 11000, 12000, 60000, 83300],
    "anchor_day": 9650,
    "history_b64": "AAAA",
    "streak": 21,
    "current_streak": 6,
    "devices": [
        {"device_id": "A1", "device": "CrossInk", "updated_at": 1752345678},
        {"device_id": "B2", "device": "X3", "updated_at": 1752300000},
    ],
}


class FakeSync:
    """Accept one user; optionally fail with 429 or 500."""

    def __init__(self, username: str = "alice", password: str = "secret") -> None:
        self.users = {username: hashlib.md5(password.encode()).hexdigest()}
        self.summary = dict(SUMMARY)
        self.fail_status: int | None = None
        app = web.Application()
        app.router.add_get("/users/auth", self._auth)
        app.router.add_get("/api/v1/stats/summary", self._summary)
        self.server = TestServer(app)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.port}"

    def _check(self, request: web.Request) -> web.Response | None:
        if self.fail_status:
            return web.Response(status=self.fail_status, text="nope")
        user = request.headers.get("x-auth-user")
        if self.users.get(user) != request.headers.get("x-auth-key"):
            return web.json_response(
                {"code": 2001, "message": "Unauthorized"}, status=401
            )
        return None

    async def _auth(self, request: web.Request) -> web.Response:
        return self._check(request) or web.json_response({"authorized": "OK"})

    async def _summary(self, request: web.Request) -> web.Response:
        return self._check(request) or web.json_response(self.summary)
