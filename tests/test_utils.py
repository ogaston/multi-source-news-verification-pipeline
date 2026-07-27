"""Unit tests for utils helpers (no Chroma/embedding model required)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

import utils
from sources import NewsSource


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_news.db"
    monkeypatch.setattr(utils, "DB_NAME", str(db_path))
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
                    "id-b",
                    "Hoy",
                    "Second",
                    "2026-07-20T12:00:00+00:00",
                    "b" * 100,
                    "https://example.com/b",
                ),
                (
                    "id-a",
                    "Acento",
                    "First",
                    "2026-07-21T12:00:00+00:00",
                    "a" * 100,
                    "https://example.com/a",
                ),
            ],
        )
        conn.commit()
    return db_path


class TestParseArticleDate:
    def test_none_and_empty(self):
        assert utils.parse_article_date(None) is None
        assert utils.parse_article_date("") is None
        assert utils.parse_article_date("sin fecha") is None

    def test_iso_with_z(self):
        dt = utils.parse_article_date("2026-07-21T15:30:00Z")
        assert dt == datetime(2026, 7, 21, 15, 30, tzinfo=timezone.utc)

    def test_iso_with_offset(self):
        dt = utils.parse_article_date("2026-07-21T12:00:00+00:00")
        assert dt == datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)

    def test_unparseable(self):
        assert utils.parse_article_date("not-a-date") is None


class TestFilterRankedIds:
    threshold = datetime(2026, 7, 20, tzinfo=timezone.utc)

    def test_filters_by_date_and_preserves_rank_order(self):
        ranked = ["old", "fresh", "also-fresh"]
        metas = [
            {"source": "Acento", "date": "2026-07-10T00:00:00+00:00"},
            {"source": "Acento", "date": "2026-07-21T00:00:00+00:00"},
            {"source": "Hoy", "date": "2026-07-22T00:00:00+00:00"},
        ]
        assert utils.filter_ranked_ids(
            ranked,
            metas,
            date_threshold=self.threshold,
            source=None,
            limit=10,
        ) == ["fresh", "also-fresh"]

    def test_filters_by_source(self):
        ranked = ["a", "b"]
        metas = [
            {"source": "Acento", "date": "2026-07-21T00:00:00+00:00"},
            {"source": "Hoy", "date": "2026-07-21T00:00:00+00:00"},
        ]
        assert utils.filter_ranked_ids(
            ranked,
            metas,
            date_threshold=self.threshold,
            source=NewsSource.ACENTO,
            limit=10,
        ) == ["a"]

    def test_respects_limit(self):
        ranked = ["a", "b", "c"]
        metas = [
            {"source": "Hoy", "date": "2026-07-21T00:00:00+00:00"},
            {"source": "Hoy", "date": "2026-07-22T00:00:00+00:00"},
            {"source": "Hoy", "date": "2026-07-23T00:00:00+00:00"},
        ]
        assert utils.filter_ranked_ids(
            ranked,
            metas,
            date_threshold=self.threshold,
            source=None,
            limit=2,
        ) == ["a", "b"]

    def test_skips_missing_date_and_none_meta(self):
        ranked = ["no-date", "ok", "null-meta"]
        metas = [
            {"source": "Hoy"},
            {"source": "Hoy", "date": "2026-07-21T00:00:00+00:00"},
            None,
        ]
        assert utils.filter_ranked_ids(
            ranked,
            metas,
            date_threshold=self.threshold,
            source=None,
            limit=10,
        ) == ["ok"]


class TestFormatRagContext:
    def test_formats_rows(self):
        row = {
            "source": "Acento",
            "date": "2026-07-21",
            "title": "Headline",
            "url": "https://example.com/x",
            "content": "hello world",
        }
        text = utils.format_rag_context("apagones", [row])
        assert "--- RAG CONTEXT FOR TOPIC: 'apagones' ---" in text
        assert "SOURCE: Acento" in text
        assert "HEADLINE: Headline" in text
        assert "CONTENT EXCERPT:\nhello world...\n" in text

    def test_truncates_long_content(self):
        row = {
            "source": "Hoy",
            "date": "2026-07-21",
            "title": "T",
            "url": "https://example.com/y",
            "content": "x" * 3000,
        }
        text = utils.format_rag_context("topic", [row])
        assert "CONTENT EXCERPT:\n" + ("x" * 2500) + "...\n" in text
        assert "x" * 2501 not in text


class TestQueryDbAndLoadOrderedRows:
    def test_query_db(self, temp_db):
        rows = utils.query_db("SELECT id, title FROM news WHERE id = ?", ("id-a",))
        assert len(rows) == 1
        assert rows[0]["title"] == "First"

    def test_load_ordered_rows_preserves_input_order(self, temp_db):
        ordered = utils.load_ordered_rows(["id-a", "id-b"])
        assert [row["id"] for row in ordered] == ["id-a", "id-b"]

    def test_load_ordered_rows_skips_missing_ids(self, temp_db):
        ordered = utils.load_ordered_rows(["missing", "id-b"])
        assert [row["id"] for row in ordered] == ["id-b"]
