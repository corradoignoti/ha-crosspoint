"""Reading statistics from CrossPoint Sync, one coordinator per user."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api.errors import CrossPointError
from .api.sync import (
    CrossPointSyncAuthError,
    CrossPointSyncClient,
    CrossPointSyncRateLimitError,
)
from .const import CONF_SYNC_KEY, CONF_SYNC_URL, CONF_SYNC_USERNAME, DOMAIN

if TYPE_CHECKING:
    from . import CrossPointConfigEntry

_LOGGER = logging.getLogger(__name__)

STATS_POLL_INTERVAL = timedelta(minutes=30)
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
TIMES_OF_DAY = ("morning", "afternoon", "evening", "night")


def _number(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    return int(value) if isinstance(value, (int, float)) else 0


def _minutes(values: Any, labels: tuple[str, ...]) -> dict[str, int]:
    if not isinstance(values, list) or len(values) != len(labels):
        return {}
    return {
        label: round(v / 60) if isinstance(v, (int, float)) else 0
        for label, v in zip(labels, values, strict=True)
    }


def _streaks(activity: dict[str, Any], today: date) -> tuple[int, int]:
    """Return (current, longest) streaks of days with reading progress.

    A day counts when it has a sync or forward pages. The current streak may
    end yesterday, since today is not over.
    """
    days = set()
    for entry in activity.get("days") or []:
        if not isinstance(entry, dict) or not (
            entry.get("syncs") or entry.get("pages")
        ):
            continue
        try:
            days.add(date.fromisoformat(str(entry.get("day"))))
        except ValueError:
            continue
    longest = run = 0
    previous: date | None = None
    for day in sorted(days):
        run = run + 1 if previous and day - previous == timedelta(days=1) else 1
        longest = max(longest, run)
        previous = day
    end = today if today in days else today - timedelta(days=1)
    current = 0
    while end - timedelta(days=current) in days:
        current += 1
    return current, longest


@dataclass(frozen=True, slots=True)
class ReadingStats:
    """Combined reading statistics of one user, across devices."""

    seconds: int
    pages: int
    completed: int
    sessions: int
    longest_streak: int
    current_streak: int
    weekday_minutes: dict[str, int] = field(default_factory=dict)
    time_of_day_minutes: dict[str, int] = field(default_factory=dict)
    devices: tuple[dict[str, Any], ...] = ()
    last_upload: datetime | None = None

    @classmethod
    def from_summary(
        cls,
        summary: dict[str, Any],
        activity: dict[str, Any] | None = None,
        today: date | None = None,
    ) -> ReadingStats:
        """Build from a GET /api/v1/stats/summary response.

        Readers that never upload stats (stock CrossPoint, KOReader) leave the
        summary empty; ``activity`` (GET /api/v1/stats/activity, derived from
        the progress log) fills in pages, finished books and streaks.
        """
        devices = tuple(
            {
                "device_id": str(d.get("device_id", "")),
                "device": str(d.get("device", "")),
                "updated_at": d.get("updated_at"),
            }
            for d in summary.get("devices") or []
            if isinstance(d, dict)
        )
        uploads = [
            d["updated_at"]
            for d in devices
            if isinstance(d["updated_at"], (int, float))
        ]
        pages = _number(summary, "pages")
        completed = _number(summary, "completed")
        longest = _number(summary, "streak")
        current = _number(summary, "current_streak")
        if activity:
            pages = max(pages, _number(activity, "pages_total"))
            completed = max(
                completed,
                sum(
                    1
                    for b in activity.get("books") or []
                    if isinstance(b, dict) and b.get("finished_at")
                ),
            )
            act_current, act_longest = _streaks(activity, today or dt_util.now().date())
            longest = max(longest, act_longest)
            current = max(current, act_current)
        return cls(
            seconds=_number(summary, "seconds"),
            pages=pages,
            completed=completed,
            sessions=_number(summary, "sessions"),
            longest_streak=longest,
            current_streak=current,
            weekday_minutes=_minutes(summary.get("dow"), WEEKDAYS),
            time_of_day_minutes=_minutes(summary.get("tod"), TIMES_OF_DAY),
            devices=devices,
            last_upload=(dt_util.utc_from_timestamp(max(uploads)) if uploads else None),
        )


class ReadingStatsCoordinator(DataUpdateCoordinator[ReadingStats]):
    """Poll the reading statistics of one CrossPoint Sync user.

    This only talks to the sync server, so it works whether or not the
    e-reader is reachable.
    """

    config_entry: CrossPointConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: CrossPointConfigEntry,
        subentry: ConfigSubentry,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} stats {subentry.data[CONF_SYNC_USERNAME]}",
            update_interval=STATS_POLL_INTERVAL,
        )
        self.subentry = subentry
        self.client = CrossPointSyncClient(
            async_get_clientsession(hass),
            subentry.data[CONF_SYNC_URL],
            subentry.data[CONF_SYNC_USERNAME],
            subentry.data[CONF_SYNC_KEY],
        )

    @property
    def _issue_id(self) -> str:
        return f"sync_auth_failed_{self.subentry.subentry_id}"

    async def _async_update_data(self) -> ReadingStats:
        try:
            summary = await self.client.async_summary()
        except CrossPointSyncAuthError as err:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                self._issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key="sync_auth_failed",
                translation_placeholders={
                    "username": self.client.username,
                    "url": self.client.url,
                },
            )
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="sync_auth_failed",
                translation_placeholders={"username": self.client.username},
            ) from err
        except CrossPointSyncRateLimitError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN, translation_key="sync_rate_limited"
            ) from err
        except CrossPointError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="sync_unavailable",
                translation_placeholders={"error": str(err)},
            ) from err
        ir.async_delete_issue(self.hass, DOMAIN, self._issue_id)
        try:
            activity = await self.client.async_activity(self._tz_offset())
        except CrossPointError as err:
            # Older servers lack the endpoint; the summary alone is still valid.
            _LOGGER.debug("No activity stats for %s: %s", self.client.username, err)
            activity = None
        return ReadingStats.from_summary(summary, activity)

    def _tz_offset(self) -> int:
        """Return the local UTC offset in minutes, as JS getTimezoneOffset()."""
        offset = dt_util.now().utcoffset() or timedelta()
        return -int(offset.total_seconds() // 60)
