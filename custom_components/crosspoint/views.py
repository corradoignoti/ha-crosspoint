"""HTTP views of the CrossPoint integration."""

from __future__ import annotations

import re

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.http import KEY_HASS

from .const import DOMAIN

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class CrossPointCoverView(HomeAssistantView):
    """Serve cached book cover thumbnails.

    Authentication is required. Image tags in the panel use signed paths
    (``auth/sign_path``) to load them.
    """

    url = "/api/crosspoint/{entry_id}/cover/{sha256}"
    name = "api:crosspoint:cover"
    requires_auth = True

    async def get(
        self, request: web.Request, entry_id: str, sha256: str
    ) -> web.StreamResponse:
        """Return the JPEG thumbnail of one book."""
        hass = request.app[KEY_HASS]
        entry = hass.config_entries.async_get_entry(entry_id)
        if (
            not _SHA256.match(sha256)
            or entry is None
            or entry.domain != DOMAIN
            or getattr(entry, "runtime_data", None) is None
        ):
            raise web.HTTPNotFound
        path = entry.runtime_data.library.cover_path(sha256)
        if path is None:
            raise web.HTTPNotFound
        return web.FileResponse(
            path,
            headers={
                "Content-Type": "image/jpeg",
                # Content-addressed by hash: safe to cache for a long time.
                "Cache-Control": "private, max-age=31536000, immutable",
            },
        )
