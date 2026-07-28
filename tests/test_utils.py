"""Unit tests for utils helpers (no Chroma/embedding model required)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

import mcp_app.utils as utils
from common.indexing import RetrievedChunk
from common.sources import NewsSource


def _chunk(
    article_id: str,
    *,
    source: str = "Hoy",
    date: str = "2026-07-21T00:00:00+00:00",
    title: str = "T",
    url: str = "https://example.com/x",
    text: str = "chunk text",
    score: float = 0.9,
    chunk_index: int = 0,
) -> RetrievedChunk:
    return RetrievedChunk(
        article_id=article_id,
        text=text,
        score=score,
        url=url,
        source=source,
        title=title,
        date=date,
        chunk_index=chunk_index,
    )


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


class TestFilterRankedChunks:
    threshold = datetime(2026, 7, 20, tzinfo=timezone.utc)

    def test_filters_by_date_and_preserves_rank_order(self):
        chunks = [
            _chunk("old", date="2026-07-10T00:00:00+00:00", source="Acento"),
            _chunk("fresh", date="2026-07-21T00:00:00+00:00", source="Acento"),
            _chunk("also-fresh", date="2026-07-22T00:00:00+00:00", source="Hoy"),
        ]
        result = utils.filter_ranked_chunks(
            chunks,
            date_threshold=self.threshold,
            source=None,
            limit=10,
        )
        assert [c.article_id for c in result] == ["fresh", "also-fresh"]

    def test_filters_by_source(self):
        chunks = [
            _chunk("a", source="Acento"),
            _chunk("b", source="Hoy"),
        ]
        result = utils.filter_ranked_chunks(
            chunks,
            date_threshold=self.threshold,
            source=NewsSource.ACENTO,
            limit=10,
        )
        assert [c.article_id for c in result] == ["a"]

    def test_respects_limit(self):
        chunks = [
            _chunk("a", date="2026-07-21T00:00:00+00:00"),
            _chunk("b", date="2026-07-22T00:00:00+00:00"),
            _chunk("c", date="2026-07-23T00:00:00+00:00"),
        ]
        result = utils.filter_ranked_chunks(
            chunks,
            date_threshold=self.threshold,
            source=None,
            limit=2,
        )
        assert [c.article_id for c in result] == ["a", "b"]

    def test_skips_missing_date(self):
        chunks = [
            _chunk("no-date", date=""),
            _chunk("ok", date="2026-07-21T00:00:00+00:00"),
        ]
        result = utils.filter_ranked_chunks(
            chunks,
            date_threshold=self.threshold,
            source=None,
            limit=10,
        )
        assert [c.article_id for c in result] == ["ok"]

    def test_dedupes_by_article_keeping_first_ranked(self):
        chunks = [
            _chunk("art-1", text="best", score=0.95, chunk_index=1),
            _chunk("art-1", text="worse", score=0.5, chunk_index=0),
            _chunk("art-2", text="other", score=0.4),
        ]
        result = utils.filter_ranked_chunks(
            chunks,
            date_threshold=self.threshold,
            source=None,
            limit=10,
        )
        assert [c.article_id for c in result] == ["art-1", "art-2"]
        assert result[0].text == "best"


class TestFormatRagContext:
    def test_formats_chunks(self):
        chunk = _chunk(
            "id-1",
            source="Acento",
            date="2026-07-21",
            title="Headline",
            url="https://example.com/x",
            text="hello world",
        )
        text = utils.format_rag_context("apagones", [chunk])
        assert "--- RAG CONTEXT FOR TOPIC: 'apagones' ---" in text
        assert "SOURCE: Acento" in text
        assert "HEADLINE: Headline" in text
        assert "CHUNK:\nhello world\n" in text

    def test_includes_full_chunk_text(self):
        body = "x" * 3000
        chunk = _chunk("id-2", source="Hoy", title="T", text=body)
        text = utils.format_rag_context("topic", [chunk])
        assert f"CHUNK:\n{body}\n" in text


class TestQueryDb:
    def test_query_db(self, temp_db):
        rows = utils.query_db("SELECT id, title FROM news WHERE id = ?", ("id-a",))
        assert len(rows) == 1
        assert rows[0]["title"] == "First"
