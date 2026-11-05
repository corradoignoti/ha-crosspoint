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
