"""Sensor entities for reading statistics (one device per sync user)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTime
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SYNC_URL, CONF_SYNC_USERNAME, DOMAIN
from .stats import ReadingStats, ReadingStatsCoordinator


@dataclass(frozen=True, kw_only=True)
class ReadingStatsSensorDescription(SensorEntityDescription):
    """Describe one reading statistics sensor."""

    value: Callable[[ReadingStats], int | datetime | None]
    attributes: Callable[[ReadingStats], dict[str, Any]] | None = None


STATS_SENSORS: tuple[ReadingStatsSensorDescription, ...] = (
    ReadingStatsSensorDescription(
        key="reading_time",
        translation_key="reading_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=1,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value=lambda s: s.seconds,
        attributes=lambda s: {
            "weekday_minutes": s.weekday_minutes,
            "time_of_day_minutes": s.time_of_day_minutes,
        },
    ),
    ReadingStatsSensorDescription(
        key="pages",
        translation_key="pages_read",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value=lambda s: s.pages,
    ),
    ReadingStatsSensorDescription(
        key="completed",
        translation_key="books_finished",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value=lambda s: s.completed,
    ),
    ReadingStatsSensorDescription(
        key="sessions",
        translation_key="reading_sessions",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value=lambda s: s.sessions,
    ),
    ReadingStatsSensorDescription(
        key="current_streak",
        translation_key="current_streak",
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda s: s.current_streak,
    ),
    ReadingStatsSensorDescription(
        key="longest_streak",
        translation_key="longest_streak",
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda s: s.longest_streak,
    ),
    ReadingStatsSensorDescription(
        key="last_upload",
        translation_key="last_upload",
        device_class=SensorDeviceClass.TIMESTAMP,
        value=lambda s: s.last_upload,
        attributes=lambda s: {"devices": [d["device"] for d in s.devices]},
    ),
)


class ReadingStatsSensor(CoordinatorEntity[ReadingStatsCoordinator], SensorEntity):
    """One reading statistic of one CrossPoint Sync user."""

    _attr_has_entity_name = True
    entity_description: ReadingStatsSensorDescription

    def __init__(
        self,
        coordinator: ReadingStatsCoordinator,
        description: ReadingStatsSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        subentry = coordinator.subentry
        self._attr_unique_id = f"{subentry.subentry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"sync_{subentry.subentry_id}")},
            name=f"CrossPoint Sync {subentry.data[CONF_SYNC_USERNAME]}",
            manufacturer="CrossPoint Sync",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=subentry.data[CONF_SYNC_URL],
        )

    @property
    def native_value(self) -> int | datetime | None:
        """Return the statistic."""
        return self.entity_description.value(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return breakdowns (weekday, time of day, devices)."""
        if self.entity_description.attributes is None:
            return None
        return self.entity_description.attributes(self.coordinator.data)
