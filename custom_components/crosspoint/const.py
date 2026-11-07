"""Constants for the CrossPoint integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

DOMAIN: Final = "crosspoint"

CONF_MODEL: Final = "model"
CONF_WS_PORT: Final = "ws_port"
CONF_LIBRARY_PATH: Final = "library_path"
CONF_BOOKS_DIR: Final = "books_dir"
CONF_WALLPAPERS_DIR: Final = "wallpapers_dir"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_DEVICE_BOOKS_DIR: Final = "device_books_dir"
CONF_SYNC_URL: Final = "url"
CONF_SYNC_USERNAME: Final = "username"
CONF_SYNC_KEY: Final = "key"

SUBENTRY_SYNC_USER: Final = "sync_user"
DEFAULT_SYNC_URL: Final = "https://sync.crosspointreader.com"

DEFAULT_HOST: Final = "crosspoint.local"
DEFAULT_HTTP_PORT: Final = 80
DEFAULT_WS_PORT: Final = 81
DISCOVERY_PORT: Final = 8134
DISCOVERY_PAYLOAD: Final = b"hello"
DISCOVERY_TIMEOUT: Final = 2.0

DEFAULT_LIBRARY_PATH: Final = "/media/crosspoint"
DEFAULT_BOOKS_DIR: Final = "books"
DEFAULT_WALLPAPERS_DIR: Final = "wallpapers"
DEFAULT_SCAN_INTERVAL_MIN: Final = 30
DEVICE_POLL_INTERVAL_S: Final = 20
# Minimum delay between two discovery broadcasts while the reader is unreachable.
REDISCOVERY_INTERVAL_S: Final = 60
# Plugin name sent to /api/status; the firmware derives the unit ID from it.
DEVICE_ID_PLUGIN: Final = "home-assistant-crosspoint"
DEFAULT_DEVICE_BOOKS_DIR: Final = "/Books"
# Sleep screen folders read by the firmware (it picks one image at random).
DEVICE_SLEEP_DIR: Final = "/.sleep"
DEVICE_SLEEP_OVERLAY_DIR: Final = "/.sleep-overlay"

EVENT_UPLOAD_PROGRESS: Final = f"{DOMAIN}_upload_progress"

KIND_BOOK: Final = "book"
KIND_WALLPAPER: Final = "wallpaper"


@dataclass(frozen=True, slots=True)
class DeviceModel:
    """A supported e-reader model and its screen resolution (portrait)."""

    key: str
    name: str
    width: int
    height: int


MODELS: Final[dict[str, DeviceModel]] = {
    model.key: model
    for model in (
        DeviceModel("xteink_x4", "Xteink X4", 480, 800),
        DeviceModel("xteink_x3", "Xteink X3", 528, 792),
        DeviceModel("cross_share", "Cross-Share", 480, 800),
    )
}
DEFAULT_MODEL: Final = "xteink_x4"


def guess_model(device: object) -> str | None:
    """Map the firmware ``device`` status field to a known model key.

    Real values include ``xteink_x4_classic``; unknown values return None.
    """
    name = str(device or "").lower().replace("-", " ")
    if "x3" in name:
        return "xteink_x3"
    if "x4" in name:
        return "xteink_x4"
    if "cross share" in name or "crossshare" in name or "cross_share" in name:
        return "cross_share"
    return None
