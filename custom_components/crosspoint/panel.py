"""Sidebar panel and Lovelace card of the CrossPoint integration."""

from __future__ import annotations

import json
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PANEL_URL_PATH = DOMAIN
PANEL_COMPONENT = "crosspoint-panel"
STATIC_URL = f"/{DOMAIN}_static"
_FRONTEND_DIR = Path(__file__).parent / "frontend"
_DATA_STATIC = f"{DOMAIN}_static_registered"
CARD_FILE = "crosspoint-stats-card.js"


def _version() -> str:
    manifest = json.loads((Path(__file__).parent / "manifest.json").read_text())
    return str(manifest["version"])


async def async_register_panel(hass: HomeAssistant) -> None:
    """Register the sidebar panel (once, while at least one entry is loaded).

    The first call also serves the frontend files and loads the reading stats
    card on every dashboard; neither can be undone until a restart.
    """
    version = await hass.async_add_executor_job(_version)
    if not hass.data.get(_DATA_STATIC):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(_FRONTEND_DIR), cache_headers=False)]
        )
        frontend.add_extra_js_url(hass, f"{STATIC_URL}/{CARD_FILE}?v={version}")
        hass.data[_DATA_STATIC] = True
    if PANEL_URL_PATH in hass.data.get(frontend.DATA_PANELS, {}):
        return
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_COMPONENT,
        sidebar_title="CrossPoint",
        sidebar_icon="mdi:book-open-page-variant",
        # The version busts the browser cache after an update.
        module_url=f"{STATIC_URL}/crosspoint-panel.js?v={version}",
        require_admin=True,
    )


def async_unregister_panel(hass: HomeAssistant) -> None:
    """Remove the sidebar panel."""
    frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
