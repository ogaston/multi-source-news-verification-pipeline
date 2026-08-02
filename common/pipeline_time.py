"""Local calendar helpers for pipeline batch windows."""

from __future__ import annotations

from datetime import date, datetime, timedelta, time
from zoneinfo import ZoneInfo

from common.config import PIPELINE_TZ, PREPROCESS_DAY_OFFSET


def pipeline_zone() -> ZoneInfo:
    return ZoneInfo(PIPELINE_TZ)


def now_pipeline_iso() -> str:
    """Current local wall-clock timestamp (naive ISO, implicit PIPELINE_TZ)."""
    return datetime.now(pipeline_zone()).replace(tzinfo=None).isoformat()


def local_day_bounds(
    day: date,
    *,
    tz_name: str | None = None,
) -> tuple[str, str]:
    """
    Half-open local-day window [day 00:00, next day 00:00) as naive ISO strings.
    """
    tz = ZoneInfo(tz_name or PIPELINE_TZ)
    start = datetime.combine(day, time.min, tzinfo=tz).replace(tzinfo=None)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()


def resolve_preprocess_day(
    *,
    explicit_date: date | None = None,
    day_offset: int = PREPROCESS_DAY_OFFSET,
    now: datetime | None = None,
) -> date:
    """Return the local calendar day to preprocess (default: previous local day)."""
    if explicit_date is not None:
        return explicit_date
    current = now.astimezone(pipeline_zone()) if now else datetime.now(pipeline_zone())
    return (current.date() - timedelta(days=max(0, day_offset)))
