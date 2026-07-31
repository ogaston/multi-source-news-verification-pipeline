"""Tests for MCP search tools input clamping (no Chroma required)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

import common.db as db
import mcp_app.tools as tools
from common.config import MAX_DAYS_BACK, MAX_QUERY_LIMIT, MAX_TOPIC_LENGTH
from common.indexing import RetrievedChunk, RetrievedStory
from tests.conftest import insert_raw_articles


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
def stories_db(sqlalchemy_db):
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(hours=3)).isoformat()
    older = (now - timedelta(days=5)).isoformat()

    insert_raw_articles(
        [
            {
                "id": "a1",
                "url": "https://example.com/a1",
                "source": "Hoy",
                "title": "Apagón en la capital",
                "content": "Contenido Hoy sobre apagones",
                "date": recent,
                "processed": 0,
            },
            {
                "id": "a2",
                "url": "https://example.com/a2",
                "source": "Acento",
                "title": "Crisis eléctrica",
                "content": "Contenido Acento sobre apagones",
                "date": recent,
                "processed": 0,
            },
            {
                "id": "a3",
                "url": "https://example.com/a3",
                "source": "Hoy",
                "title": "Vieja noticia",
                "content": "Contenido viejo",
                "date": older,
                "processed": 0,
            },
        ]
    )
    with db.get_engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO clusters (cluster_id, description, created_at, processed)
                VALUES (:cluster_id, :description, :created_at, 0)
                """
            ),
            [
                {
                    "cluster_id": "story-multi",
                    "description": "Apagones en el país",
                    "created_at": "2026-07-29T00:00:00Z",
                },
                {
                    "cluster_id": "story-old",
                    "description": "Historia antigua",
                    "created_at": "2026-07-20T00:00:00Z",
                },
            ],
        )
        conn.execute(
            text(
                """
                INSERT INTO topic_clusters (cluster_id, article_id, created_at)
                VALUES (:cluster_id, :article_id, :created_at)
                """
            ),
            [
                {
                    "cluster_id": "story-multi",
                    "article_id": "a1",
                    "created_at": "2026-07-29T00:00:00Z",
                },
                {
                    "cluster_id": "story-multi",
                    "article_id": "a2",
                    "created_at": "2026-07-29T00:00:00Z",
                },
                {
                    "cluster_id": "story-old",
                    "article_id": "a3",
                    "created_at": "2026-07-20T00:00:00Z",
                },
            ],
        )
    return sqlalchemy_db


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


@pytest.fixture
def verified_db(sqlalchemy_db, monkeypatch):
    monkeypatch.setattr(db, "index_verified_article", lambda **_k: None)
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(hours=3)).isoformat()
    older = (now - timedelta(days=5)).isoformat()
    with db.get_engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO verified_articles (
                    id, cluster_id, slug, title, content, image_url, date,
                    sources, status, confidence, confidence_score, created_at
                )
                VALUES (
                    :id, :cluster_id, :slug, :title, :content, NULL, :date,
                    :sources, :status, :confidence, :confidence_score, :created_at
                )
                """
            ),
            [
                {
                    "id": "v1",
                    "cluster_id": "cluster-recent",
                    "slug": "apagones-cluster",
                    "title": "Apagones en la capital",
                    "content": "Cuerpo verificado sobre apagones.",
                    "date": recent,
                    "sources": "Hoy, Acento",
                    "status": "draft",
                    "confidence": "alta",
                    "confidence_score": 0.91,
                    "created_at": recent,
                },
                {
                    "id": "v2",
                    "cluster_id": "cluster-old",
                    "slug": "historia-vieja",
                    "title": "Historia antigua",
                    "content": "Cuerpo viejo.",
                    "date": older,
                    "sources": "Hoy",
                    "status": "draft",
                    "confidence": None,
                    "confidence_score": None,
                    "created_at": older,
                },
                {
                    "id": "v3",
                    "cluster_id": "cluster-published",
                    "slug": "reforma-publicada",
                    "title": "Reforma fiscal publicada",
                    "content": "Cuerpo publicado.",
                    "date": recent,
                    "sources": "Listin Diario",
                    "status": "published",
                    "confidence": None,
                    "confidence_score": None,
                    "created_at": recent,
                },
            ],
        )
    return sqlalchemy_db


def test_list_verified_clamps_limit_and_days_back(monkeypatch, verified_db):
    captured: dict = {}
    real_fetch = tools.fetch_verified_articles

    def wrapped_fetch(date_threshold, *, status=None, limit=20):
        captured["limit"] = limit
        captured["date_threshold"] = date_threshold
        captured["status"] = status
        return real_fetch(date_threshold, status=status, limit=limit)

    monkeypatch.setattr(tools, "fetch_verified_articles", wrapped_fetch)
    tools.run_list_verified_articles(days_back=10_000, limit=10_000)

    assert captured["limit"] == MAX_QUERY_LIMIT
    age = datetime.now(timezone.utc) - datetime.fromisoformat(
        captured["date_threshold"]
    )
    assert abs(age.days - MAX_DAYS_BACK) <= 1


def test_list_verified_compact_excludes_old_and_content(verified_db):
    result = tools.run_list_verified_articles(days_back=1, limit=20)

    assert "VERIFIED LIST" in result
    assert "CLUSTER_ID: cluster-recent" in result
    assert "SLUG: apagones-cluster" in result
    assert "CONFIDENCE: alta" in result
    assert "CONFIDENCE_SCORE: 0.91" in result
    assert "CONTENT:" not in result
    assert "cluster-old" not in result


def test_list_verified_status_filter(verified_db):
    result = tools.run_list_verified_articles(
        days_back=1, limit=20, status="published"
    )
    assert "cluster-published" in result
    assert "cluster-recent" not in result


def test_list_verified_empty(monkeypatch, verified_db):
    monkeypatch.setattr(tools, "fetch_verified_articles", lambda *_a, **_k: [])
    result = tools.run_list_verified_articles(days_back=1)
    assert "No verified articles found" in result
    assert "last 1 day" in result


def test_get_verified_full_body(verified_db):
    result = tools.run_get_verified_article("cluster-recent")
    assert "VERIFIED: Apagones en la capital" in result
    assert "CLUSTER_ID: cluster-recent" in result
    assert "SOURCES: Hoy, Acento" in result
    assert "CONTENT:\nCuerpo verificado sobre apagones." in result
    assert "CONFIDENCE: alta" in result


def test_get_verified_omits_null_confidence(verified_db):
    result = tools.run_get_verified_article("cluster-published")
    assert "CONFIDENCE:" not in result
    assert "CONFIDENCE_SCORE:" not in result


def test_get_verified_not_found(verified_db):
    assert "Verified article not found: 'missing'" in tools.run_get_verified_article(
        "missing"
    )
    assert "missing cluster_id" in tools.run_get_verified_article("  ")


def test_search_verified_clamps_and_formats(monkeypatch, verified_db):
    from common.indexing import RetrievedVerified

    captured: dict = {}
    hit = RetrievedVerified(
        cluster_id="cluster-recent",
        title="Apagones en la capital",
        score=0.95,
        date="2099-01-01T00:00:00+00:00",
        status="draft",
    )

    def fake_retrieve(query: str, n_results: int):
        captured["query"] = query
        captured["n_results"] = n_results
        return [hit]

    monkeypatch.setattr(tools, "retrieve_verified", fake_retrieve)

    long_query = "x" * (MAX_TOPIC_LENGTH + 100)
    result = tools.run_search_verified_articles(
        long_query, limit=10_000, days_back=10_000
    )

    assert captured["query"] == "x" * MAX_TOPIC_LENGTH
    assert "VERIFIED SEARCH" in result
    assert "CLUSTER_ID: cluster-recent" in result
    assert "CONTENT:\nCuerpo verificado sobre apagones." in result


def test_search_verified_empty_after_filter(monkeypatch, verified_db):
    from common.indexing import RetrievedVerified

    hit = RetrievedVerified(
        cluster_id="cluster-old",
        title="Historia antigua",
        score=0.9,
        date="2020-01-01T00:00:00+00:00",
        status="draft",
    )
    monkeypatch.setattr(tools, "retrieve_verified", lambda *_a, **_k: [hit])
    result = tools.run_search_verified_articles("tema", days_back=1)
    assert "No semantically relevant verified articles found" in result
