"""Tests for MCP search tools input clamping (no Chroma required)."""

from __future__ import annotations

from datetime import datetime, timezone

from common.config import MAX_DAYS_BACK, MAX_QUERY_LIMIT, MAX_TOPIC_LENGTH
from common.indexing import RetrievedChunk, RetrievedStory
import mcp_app.tools as tools


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
