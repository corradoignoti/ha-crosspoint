"""Shared fixtures for CrossPoint tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom_components in every test."""
    return


@pytest.fixture(autouse=True)
def isolated_cache_dir(hass, tmp_path):
    """Keep the Home Assistant cache directory (cover thumbnails) per test."""
    config_dir = tmp_path / "ha_config"
    config_dir.mkdir()
    hass.config.config_dir = str(config_dir)
