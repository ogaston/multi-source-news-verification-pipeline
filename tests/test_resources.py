"""Tests for MCP resource logic (sources catalog + frontpage)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

import mcp_app.utils as utils
from common.sources import NewsSource
from mcp_app.resources import get_source_frontpage, list_sources_json, resolve_source_id


@pytest.fixture
def frontpage_db(tmp_path, monkeypatch):
    db_path = tmp_path / "frontpage_news.db"
    monkeypatch.setattr(utils, "DB_NAME", str(db_path))

    now = datetime.now(timezone.utc)
    recent = (now - timedelta(hours=6)).isoformat()
    older = (now - timedelta(days=3)).isoformat()

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
                    "acento-recent",
                    "Acento",
                    "Recent Acento",
                    recent,
                    "Acento body",
                    "https://example.com/acento-recent",
                ),
                (
                    "acento-old",
                    "Acento",
                    "Old Acento",
                    older,
                    "Old body",
                    "https://example.com/acento-old",
                ),
                (
                    "hoy-recent",
                    "Hoy",
                    "Recent Hoy",
                    recent,
                    "Hoy body",
                    "https://example.com/hoy-recent",
                ),
            ],
        )
        conn.commit()
    return db_path


class TestListSourcesJson:
    def test_includes_all_news_sources(self):
        items = list_sources_json()
        assert len(items) == len(NewsSource)
        by_id = {item["id"]: item["name"] for item in items}
        for member in NewsSource:
            assert by_id[member.name.lower()] == member.value


class TestResolveSourceId:
    def test_resolves_lowercase_enum_name(self):
        assert resolve_source_id("acento") is NewsSource.ACENTO
        assert resolve_source_id("listin_diario") is NewsSource.LISTIN_DIARIO

    def test_unknown_returns_none(self):
        assert resolve_source_id("unknown_outlet") is None


class TestGetSourceFrontpage:
    def test_unknown_source_id(self):
        text = get_source_frontpage("not_a_source")
        assert "Unknown source_id" in text
        assert "acento" in text

    def test_includes_only_last_day_for_source(self, frontpage_db):
        text = get_source_frontpage("acento")
        assert "FRONTPAGE: Acento" in text
        assert "Recent Acento" in text
        assert "Acento body" in text
        assert "Old Acento" not in text
        assert "Recent Hoy" not in text

    def test_empty_when_no_recent_articles(self, frontpage_db):
        text = get_source_frontpage("diario_libre")
        assert text == "No articles found for Diario Libre in the last 1 day."
