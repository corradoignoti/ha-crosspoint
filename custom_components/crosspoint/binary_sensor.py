"""Binary sensors for the CrossPoint integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import CrossPointConfigEntry
from .entity import CrossPointDeviceEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CrossPointConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up CrossPoint binary sensors."""
    async_add_entities([CrossPointOnlineSensor(entry.runtime_data.coordinator)])


class CrossPointOnlineSensor(CrossPointDeviceEntity, BinarySensorEntity):
    """Whether the e-reader web server is reachable (File Transfer mode)."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "online"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "online")

    @property
    def available(self) -> bool:
        """Always available: offline is a valid state, not a failure."""
        return True

    @property
    def is_on(self) -> bool:
        """Return True when the device answers."""
        return self.coordinator.online
