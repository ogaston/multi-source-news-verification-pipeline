"""Tests for preprocess local calendar-day window on unprocessed articles."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import common.db as db
from common.pipeline_time import local_day_bounds, resolve_preprocess_day
from tests.conftest import insert_raw_articles

PIPELINE_TZ = "America/Santo_Domingo"


def _local_iso(day: date, hour: int = 12, minute: int = 0) -> str:
    """Naive local wall-clock ISO (implicit America/Santo_Domingo)."""
    return datetime(day.year, day.month, day.day, hour, minute, 0).isoformat()


def test_local_day_bounds_half_open():
    start, end = local_day_bounds(date(2026, 7, 31), tz_name=PIPELINE_TZ)
    assert start == "2026-07-31T00:00:00"
    assert end == "2026-08-01T00:00:00"


def test_resolve_preprocess_day_previous_local_day():
    # 2026-08-01 05:15 in Santo Domingo
    now = datetime(2026, 8, 1, 5, 15, tzinfo=ZoneInfo(PIPELINE_TZ))
    assert resolve_preprocess_day(day_offset=1, now=now) == date(2026, 7, 31)
    assert resolve_preprocess_day(explicit_date=date(2026, 7, 30), now=now) == date(
        2026, 7, 30
    )


def test_fetch_unprocessed_articles_respects_local_day(sqlalchemy_db):
    target = date(2026, 7, 31)
    day_start, day_end = local_day_bounds(target, tz_name=PIPELINE_TZ)
    insert_raw_articles(
        [
            {
                "id": "in-day",
                "url": "https://example.com/in-day",
                "source": "Hoy",
                "title": "En el dia",
                "content": "Contenido del dia " * 5,
                "date": target.isoformat(),
                "category": "Sociedad",
                "scraped_at": _local_iso(target, hour=15),
                "processed": 0,
            },
            {
                "id": "before-day",
                "url": "https://example.com/before",
                "source": "Hoy",
                "title": "Antes",
                "content": "Contenido viejo " * 5,
                "date": (target - timedelta(days=1)).isoformat(),
                "category": "Sociedad",
                "scraped_at": _local_iso(target - timedelta(days=1), hour=23),
                "processed": 0,
            },
            {
                "id": "after-midnight",
                "url": "https://example.com/after",
                "source": "Hoy",
                "title": "Despues",
                "content": "Contenido nuevo " * 5,
                "date": (target + timedelta(days=1)).isoformat(),
                "category": "Sociedad",
                # Exactly at next midnight — excluded by half-open end bound.
                "scraped_at": day_end,
                "processed": 0,
            },
        ]
    )

    rows = db.fetch_unprocessed_articles(
        limit=10, day_start=day_start, day_end=day_end
    )
    assert [row["id"] for row in rows] == ["in-day"]


def test_fetch_unprocessed_articles_includes_start_excludes_end(sqlalchemy_db):
    target = date(2026, 7, 31)
    day_start, day_end = local_day_bounds(target, tz_name=PIPELINE_TZ)
    insert_raw_articles(
        [
            {
                "id": "at-start",
                "url": "https://example.com/start",
                "source": "Hoy",
                "title": "Inicio",
                "content": "Contenido inicio " * 5,
                "date": target.isoformat(),
                "category": "Sociedad",
                "scraped_at": day_start,
                "processed": 0,
            },
            {
                "id": "just-before-end",
                "url": "https://example.com/almost",
                "source": "Hoy",
                "title": "Casi",
                "content": "Contenido casi " * 5,
                "date": target.isoformat(),
                "category": "Sociedad",
                "scraped_at": _local_iso(target, hour=23, minute=59),
                "processed": 0,
            },
        ]
    )
    rows = db.fetch_unprocessed_articles(
        limit=10, day_start=day_start, day_end=day_end
    )
    assert [row["id"] for row in rows] == ["at-start", "just-before-end"]


def test_fetch_unprocessed_articles_no_day_filter(sqlalchemy_db):
    now = datetime.now(timezone.utc)
    insert_raw_articles(
        [
            {
                "id": "old-2",
                "url": "https://example.com/old-2",
                "source": "Hoy",
                "title": "Vieja",
                "content": "Contenido " * 10,
                "date": (now - timedelta(days=3)).date().isoformat(),
                "category": "Sociedad",
                "scraped_at": _local_iso(
                    (now - timedelta(days=3)).date(), hour=10
                ),
                "processed": 0,
            },
        ]
    )
    rows = db.fetch_unprocessed_articles(limit=10)
    assert [row["id"] for row in rows] == ["old-2"]
