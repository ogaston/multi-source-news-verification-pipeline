"""Tests for MCP prompt logic (get_last_week)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

import utils
from prompt import LAST_WEEK_DAYS, run_get_last_week
from sources import NewsSource


@pytest.fixture
def last_week_db(tmp_path, monkeypatch):
    db_path = tmp_path / "last_week_news.db"
    monkeypatch.setattr(utils, "DB_NAME", str(db_path))

    now = datetime.now(timezone.utc)
    within_week = (now - timedelta(days=3)).isoformat()
    outside_week = (now - timedelta(days=10)).isoformat()

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE news (
                id TEXT PRIMARY KEY,
                source TEXT,
                title TEXT,
                date TEXT,
                content TEXT,
                url TEXT
            )
            """
        )
        conn.executemany(
            "INSERT INTO news (id, source, title, date, content, url) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    "acento-week",
                    "Acento",
                    "Acento This Week",
                    within_week,
                    "Week body",
                    "https://example.com/acento-week",
                ),
                (
                    "acento-old",
                    "Acento",
                    "Acento Old",
                    outside_week,
                    "Old body",
                    "https://example.com/acento-old",
                ),
                (
                    "hoy-week",
                    "Hoy",
                    "Hoy This Week",
                    within_week,
                    "Hoy body",
                    "https://example.com/hoy-week",
                ),
            ],
        )
        conn.commit()
    return db_path


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
