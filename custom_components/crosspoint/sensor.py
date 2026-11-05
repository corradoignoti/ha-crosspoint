"""Sensors for the CrossPoint integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import CrossPointConfigEntry
from .const import KIND_BOOK
from .entity import CrossPointDeviceEntity, CrossPointLibraryEntity
from .library import STATUS_INSTALLED, STATUS_MISSING, STATUS_MODIFIED
from .stats_entity import STATS_SENSORS, ReadingStatsSensor

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CrossPointConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up CrossPoint sensors."""
    runtime = entry.runtime_data
    async_add_entities(
        [
            CrossPointSignalSensor(runtime.coordinator),
            CrossPointLibraryBooksSensor(runtime.library),
            CrossPointInstalledBooksSensor(runtime.library),
        ]
    )
    for subentry_id, coordinator in runtime.stats.items():
        async_add_entities(
            [ReadingStatsSensor(coordinator, desc) for desc in STATS_SENSORS],
            config_subentry_id=subentry_id,
        )


class CrossPointSignalSensor(CrossPointDeviceEntity, SensorEntity):
    """Wi-Fi signal strength reported by the e-reader."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "rssi"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "rssi")

    @property
    def available(self) -> bool:
        """Only meaningful while the device is online."""
        return super().available and self.coordinator.online

    @property
    def native_value(self) -> int | None:
        """Return the RSSI in dBm."""
        value = self.coordinator.data.status.get("rssi")
        return int(value) if isinstance(value, (int, float)) else None


class CrossPointLibraryBooksSensor(CrossPointLibraryEntity, SensorEntity):
    """Number of books in the library folder."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "library_books"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "library_books")

    @property
    def native_value(self) -> int:
        """Return the number of library books."""
        return len(self.coordinator.data.books)


class CrossPointInstalledBooksSensor(CrossPointLibraryEntity, SensorEntity):
    """Number of books sent to the device and still tracked."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "installed_books"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "installed_books")

    @property
    def native_value(self) -> int:
        """Return the number of tracked books."""
        return sum(
            item.status in (STATUS_INSTALLED, STATUS_MODIFIED, STATUS_MISSING)
            for item in self.coordinator.items(KIND_BOOK)
        )

    @property
    def extra_state_attributes(self) -> dict[str, int]:
        """Break the count down by status."""
        items = self.coordinator.items(KIND_BOOK)
        return {
            "modified": sum(i.status == STATUS_MODIFIED for i in items),
            "missing_from_library": sum(i.status == STATUS_MISSING for i in items),
        }
