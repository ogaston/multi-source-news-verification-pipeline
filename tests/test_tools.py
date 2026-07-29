"""Tests for MCP search tools input clamping (no Chroma required)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

import common.db as db
import mcp_app.tools as tools
from common.config import MAX_DAYS_BACK, MAX_QUERY_LIMIT, MAX_TOPIC_LENGTH
from common.indexing import RetrievedChunk, RetrievedStory


def test_search_articles_clamps_limit_days_back_and_query(monkeypatch):
    captured: dict = {}

    def fake_retrieve(query: str, n_results: int):
        captured["query"] = query
        captured["n_results"] = n_results
        return [
            RetrievedChunk(
                article_id="a",
                text="chunk",
                score=0.9,
                url="https://example.com/a",
                source="Hoy",
                title="T",
                date="2099-01-01T00:00:00+00:00",
                chunk_index=0,
            )
        ]

    def fake_filter(*args, **kwargs):
        captured["limit"] = kwargs["limit"]
        captured["date_threshold"] = kwargs["date_threshold"]
        return []

    monkeypatch.setattr(tools, "retrieve_chunks", fake_retrieve)
    monkeypatch.setattr(tools, "filter_ranked_chunks", fake_filter)

    long_query = "x" * (MAX_TOPIC_LENGTH + 100)
    result = tools.run_search_articles(long_query, limit=10_000, days_back=10_000)

    assert long_query not in result
    assert ("x" * MAX_TOPIC_LENGTH) in result
    assert captured["limit"] == MAX_QUERY_LIMIT
    assert captured["query"] == "x" * MAX_TOPIC_LENGTH

    age = datetime.now(timezone.utc) - captured["date_threshold"]
    assert abs(age.days - MAX_DAYS_BACK) <= 1


def test_search_story_clamps_and_formats(monkeypatch):
    captured: dict = {}
    story = RetrievedStory(
        cluster_id="story-1",
        description="Apagones en Santo Domingo",
        score=0.95,
        created_at="2026-01-01T00:00:00Z",
    )
    articles = [
        {
            "id": "a1",
            "source": "Hoy",
            "title": "Apagón masivo",
            "date": "2099-01-01T00:00:00+00:00",
            "url": "https://example.com/a1",
            "content": "Contenido del artículo",
        }
    ]

    def fake_retrieve_stories(query: str, n_results: int):
        captured["query"] = query
        captured["n_results"] = n_results
        return [story]

    def fake_filter_stories(stories, **kwargs):
        captured["limit"] = kwargs["limit"]
        return [(story, articles)]

    monkeypatch.setattr(tools, "retrieve_stories", fake_retrieve_stories)
    monkeypatch.setattr(tools, "filter_ranked_stories", fake_filter_stories)

    result = tools.run_search_story("apagones", limit=10_000, days_back=10_000)

    assert captured["limit"] == MAX_QUERY_LIMIT
    assert "STORY: Apagones en Santo Domingo" in result
    assert "STORY_ID: story-1" in result
    assert "HEADLINE: Apagón masivo" in result


def test_search_story_empty_after_filter(monkeypatch):
    story = RetrievedStory(
        cluster_id="story-1",
        description="Tema",
        score=0.9,
        created_at="2026-01-01T00:00:00Z",
    )

    monkeypatch.setattr(
        tools,
        "retrieve_stories",
        lambda query, n_results: [story],
    )
    monkeypatch.setattr(tools, "filter_ranked_stories", lambda *_a, **_k: [])

    result = tools.run_search_story("tema", days_back=7)
    assert "No semantically relevant stories found" in result
    assert "last 7 days" in result


@pytest.fixture
def stories_db(tmp_path, monkeypatch):
    db_path = tmp_path / "stories.db"
    monkeypatch.setattr(db, "DB_NAME", str(db_path))

    now = datetime.now(timezone.utc)
    recent = (now - timedelta(hours=3)).isoformat()
    older = (now - timedelta(days=5)).isoformat()

    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE raw_articles (
                id TEXT PRIMARY KEY,
                url TEXT,
                source TEXT,
                title TEXT,
                content TEXT,
                date TEXT,
                processed INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE clusters (
                cluster_id TEXT PRIMARY KEY,
                description TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE topic_clusters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cluster_id TEXT NOT NULL,
                article_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(cluster_id, article_id)
            );
            """
        )
        conn.executemany(
            "INSERT INTO raw_articles (id, url, source, title, content, date) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    "a1",
                    "https://example.com/a1",
                    "Hoy",
                    "Apagón en la capital",
                    "Contenido Hoy sobre apagones",
                    recent,
                ),
                (
                    "a2",
                    "https://example.com/a2",
                    "Acento",
                    "Crisis eléctrica",
                    "Contenido Acento sobre apagones",
                    recent,
                ),
                (
                    "a3",
                    "https://example.com/a3",
                    "Hoy",
                    "Vieja noticia",
                    "Contenido viejo",
                    older,
                ),
            ],
        )
        conn.executemany(
            "INSERT INTO clusters (cluster_id, description, created_at) VALUES (?, ?, ?)",
            [
                ("story-multi", "Apagones en el país", "2026-07-29T00:00:00Z"),
                ("story-old", "Historia antigua", "2026-07-20T00:00:00Z"),
            ],
        )
        conn.executemany(
            "INSERT INTO topic_clusters (cluster_id, article_id, created_at) VALUES (?, ?, ?)",
            [
                ("story-multi", "a1", "2026-07-29T00:00:00Z"),
                ("story-multi", "a2", "2026-07-29T00:00:00Z"),
                ("story-old", "a3", "2026-07-20T00:00:00Z"),
            ],
        )
        conn.commit()
    return db_path


def test_list_stories_clamps_limit_and_days_back(monkeypatch, stories_db):
    captured: dict = {}

    real_fetch = tools.fetch_recent_clusters

    def wrapped_fetch(date_threshold, *, source=None, limit=20):
        captured["limit"] = limit
        captured["date_threshold"] = date_threshold
        captured["source"] = source
        return real_fetch(date_threshold, source=source, limit=limit)

    monkeypatch.setattr(tools, "fetch_recent_clusters", wrapped_fetch)

    tools.run_list_stories(days_back=10_000, limit=10_000)

    assert captured["limit"] == MAX_QUERY_LIMIT
    age = datetime.now(timezone.utc) - datetime.fromisoformat(
        captured["date_threshold"]
    )
    assert abs(age.days - MAX_DAYS_BACK) <= 1


def test_list_stories_compact_excludes_old_and_content(stories_db):
    result = tools.run_list_stories(days_back=1, limit=20)

    assert "STORY LIST" in result
    assert "STORY_ID: story-multi" in result
    assert "SOURCES: Acento, Hoy" in result
    assert "HEADLINE: Apagón en la capital" in result
    assert "CONTENT:" not in result
    assert "story-old" not in result


def test_list_stories_empty(monkeypatch, stories_db):
    monkeypatch.setattr(tools, "fetch_recent_clusters", lambda *_a, **_k: [])
    result = tools.run_list_stories(days_back=1)
    assert "No stories found" in result
    assert "last 1 day" in result


def test_get_story_full_members(stories_db):
    result = tools.run_get_story("story-multi")
    assert "STORY_ID: story-multi" in result
    assert "STORY: Apagones en el país" in result
    assert "CONTENT:\nContenido Hoy sobre apagones" in result
    assert "CONTENT:\nContenido Acento sobre apagones" in result
    assert "URL: https://example.com/a1" in result


def test_get_story_not_found(stories_db):
    assert "Story not found: 'missing'" in tools.run_get_story("missing")
    assert "Story not found: missing story_id." in tools.run_get_story("  ")
