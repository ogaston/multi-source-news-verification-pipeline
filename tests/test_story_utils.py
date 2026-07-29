"""Tests for story search formatting and filtering helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from common.indexing import RetrievedStory
from mcp_app.utils import (
    filter_ranked_stories,
    format_story_context,
    format_story_detail,
    format_story_list,
)


def _story(cluster_id: str = "s1") -> RetrievedStory:
    return RetrievedStory(
        cluster_id=cluster_id,
        description=f"Story {cluster_id}",
        score=0.9,
        created_at="2026-01-01T00:00:00Z",
    )


def test_format_story_context_includes_story_and_articles():
    story = _story("abc")
    articles = [
        {
            "source": "Hoy",
            "date": "2026-01-02",
            "title": "Titular",
            "url": "https://example.com/x",
            "content": "Texto",
        }
    ]
    text = format_story_context("apagones", [(story, articles)])
    assert "STORY: Story abc" in text
    assert "STORY_ID: abc" in text
    assert "ARTICLES: 1" in text
    assert "HEADLINE: Titular" in text


def test_filter_ranked_stories_applies_date_and_source():
    recent = {
        "source": "Hoy",
        "date": "2099-01-01T00:00:00+00:00",
        "title": "Reciente",
        "url": "https://example.com/r",
        "content": "cuerpo",
    }
    old = {
        "source": "Acento",
        "date": "2000-01-01T00:00:00+00:00",
        "title": "Viejo",
        "url": "https://example.com/o",
        "content": "cuerpo",
    }

    def fetch(cluster_id: str):
        return [recent] if cluster_id == "keep" else [old]

    threshold = datetime.now(timezone.utc)
    filtered = filter_ranked_stories(
        [_story("keep"), _story("drop")],
        fetch_articles=fetch,
        date_threshold=threshold,
        source=None,
        limit=5,
    )
    assert len(filtered) == 1
    assert filtered[0][0].cluster_id == "keep"


def test_format_story_list_is_compact():
    cluster = {
        "cluster_id": "c1",
        "description": "Tema X",
        "created_at": "2026-01-01T00:00:00Z",
    }
    articles = [
        {"source": "Hoy", "title": "Titular A", "content": "secret body"},
        {"source": "Acento", "title": "Titular B", "content": "other body"},
    ]
    text = format_story_list([(cluster, articles)], days_back=1)
    assert "STORY LIST (last 1 day)" in text
    assert "STORY_ID: c1" in text
    assert "SOURCES: Acento, Hoy" in text
    assert "HEADLINE: Titular A" in text
    assert "CONTENT:" not in text
    assert "secret body" not in text


def test_format_story_detail_includes_content():
    text = format_story_detail(
        "c1",
        "Tema X",
        "2026-01-01T00:00:00Z",
        [
            {
                "source": "Hoy",
                "date": "2026-01-02",
                "title": "Titular",
                "url": "https://example.com/x",
                "content": "Texto completo",
            }
        ],
    )
    assert "STORY_ID: c1" in text
    assert "CONTENT:\nTexto completo" in text
    assert "URL: https://example.com/x" in text
