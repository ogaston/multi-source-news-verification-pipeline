"""Tests for MCP prompt logic (get_last_week)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from common.sources import NewsSource
from mcp_app.prompt import LAST_WEEK_DAYS, run_get_last_week
from tests.conftest import insert_raw_articles


@pytest.fixture
def last_week_db(sqlalchemy_db):
    now = datetime.now(timezone.utc)
    within_week = (now - timedelta(days=3)).isoformat()
    outside_week = (now - timedelta(days=10)).isoformat()

    insert_raw_articles(
        [
            {
                "id": "acento-week",
                "source": "Acento",
                "title": "Acento This Week",
                "date": within_week,
                "content": "Week body",
                "url": "https://example.com/acento-week",
                "processed": 0,
            },
            {
                "id": "acento-old",
                "source": "Acento",
                "title": "Acento Old",
                "date": outside_week,
                "content": "Old body",
                "url": "https://example.com/acento-old",
                "processed": 0,
            },
            {
                "id": "hoy-week",
                "source": "Hoy",
                "title": "Hoy This Week",
                "date": within_week,
                "content": "Hoy body",
                "url": "https://example.com/hoy-week",
                "processed": 0,
            },
        ]
    )
    return sqlalchemy_db


class TestRunGetLastWeek:
    def test_includes_only_last_week_for_source(self, last_week_db):
        text = run_get_last_week(NewsSource.ACENTO)
        assert f"FRONTPAGE: Acento (last {LAST_WEEK_DAYS} days)" in text
        assert "Acento This Week" in text
        assert "Week body" in text
        assert "Acento Old" not in text
        assert "Hoy This Week" not in text

    def test_empty_when_no_recent_articles(self, last_week_db):
        text = run_get_last_week(NewsSource.DIARIO_LIBRE)
        assert text == (
            f"No articles found for Diario Libre in the last {LAST_WEEK_DAYS} days."
        )
