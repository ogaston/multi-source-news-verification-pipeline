"""Tests for homepage lead tiebreak and 1+8+8 slot split."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text

import common.db as db
from api.app import app
from common.homepage_rank import (
    apply_lead_tiebreak,
    llm_pick_lead_slug,
    split_home_articles,
)
from tests.conftest import insert_raw_articles


def test_apply_lead_tiebreak_skips_when_unique_max():
    rows = [
        {"slug": "a", "cluster_size": 5, "title": "A"},
        {"slug": "b", "cluster_size": 3, "title": "B"},
    ]
    called = {"n": 0}

    def picker(_tied):
        called["n"] += 1
        return "b"

    assert [r["slug"] for r in apply_lead_tiebreak(rows, pick_lead=picker)] == [
        "a",
        "b",
    ]
    assert called["n"] == 0


def test_apply_lead_tiebreak_moves_chosen_lead():
    rows = [
        {"slug": "a", "cluster_size": 4, "title": "A"},
        {"slug": "b", "cluster_size": 4, "title": "B"},
        {"slug": "c", "cluster_size": 2, "title": "C"},
    ]
    out = apply_lead_tiebreak(rows, pick_lead=lambda _tied: "b")
    assert [r["slug"] for r in out] == ["b", "a", "c"]


def test_apply_lead_tiebreak_ignores_unknown_slug():
    rows = [
        {"slug": "a", "cluster_size": 4, "title": "A"},
        {"slug": "b", "cluster_size": 4, "title": "B"},
    ]
    out = apply_lead_tiebreak(rows, pick_lead=lambda _tied: "missing")
    assert [r["slug"] for r in out] == ["a", "b"]


def test_llm_pick_lead_slug_uses_shared_chat_client(monkeypatch):
    monkeypatch.setattr("common.homepage_rank.DEEPINFRA_API_KEY", "test-key")
    candidates = [
        {"slug": "primera", "title": "Primera", "content": "Resumen uno"},
        {"slug": "segunda", "title": "Segunda", "content": "Resumen dos"},
    ]
    with patch(
        "common.homepage_rank.chat_completion",
        return_value="segunda",
    ) as mock_chat:
        assert llm_pick_lead_slug(candidates) == "segunda"

    kwargs = mock_chat.call_args.kwargs
    assert kwargs["api_key"] == "test-key"
    assert kwargs["timeout"] == 30.0
    assert kwargs["max_retries"] == 3
    assert kwargs["temperature"] == 0
    assert kwargs["max_tokens"] == 64


def test_llm_pick_lead_slug_uses_first_candidate_without_key(monkeypatch):
    monkeypatch.setattr("common.homepage_rank.DEEPINFRA_API_KEY", "")
    candidates = [{"slug": "primera"}, {"slug": "segunda"}]
    with patch("common.homepage_rank.chat_completion") as mock_chat:
        assert llm_pick_lead_slug(candidates) == "primera"
    mock_chat.assert_not_called()


def test_split_home_articles_one_plus_eight_plus_eight():
    items = [f"a{i}" for i in range(20)]
    lead, secondary, listing = split_home_articles(items)
    assert lead == "a0"
    assert secondary == [f"a{i}" for i in range(1, 9)]
    assert listing == [f"a{i}" for i in range(9, 17)]


def test_split_home_articles_empty():
    lead, secondary, listing = split_home_articles([])
    assert lead is None
    assert secondary == []
    assert listing == []


def _seed_published_with_cluster(
    *,
    article_id: str,
    cluster_id: str,
    slug: str,
    title: str,
    member_count: int,
    sources: list[str],
    created_at: str,
) -> None:
    with db.get_engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO clusters (
                    cluster_id, description, category, place, created_at, processed
                )
                VALUES (
                    :cluster_id, 'desc', 'Política', 'Santo Domingo',
                    :created_at, 1
                )
                """
            ),
            {"cluster_id": cluster_id, "created_at": created_at},
        )
    raw_rows = []
    membership = []
    for i in range(member_count):
        aid = f"{cluster_id}-m{i}"
        raw_rows.append(
            {
                "id": aid,
                "url": f"https://example.com/{aid}",
                "source": sources[i % len(sources)],
                "title": f"{title} {i}",
                "content": "body " * 20,
                "date": created_at[:10],
                "category": "Política",
                "scraped_at": created_at,
                "processed": 1,
            }
        )
        membership.append(
            {
                "cluster_id": cluster_id,
                "article_id": aid,
                "created_at": created_at,
            }
        )
    insert_raw_articles(raw_rows)
    with db.get_engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO topic_clusters (cluster_id, article_id, created_at)
                VALUES (:cluster_id, :article_id, :created_at)
                """
            ),
            membership,
        )
        conn.execute(
            text(
                """
                INSERT INTO verified_articles (
                    id, cluster_id, slug, title, content, category, image_url,
                    date, sources, status, confidence, confidence_score, created_at
                )
                VALUES (
                    :id, :cluster_id, :slug, :title, :content, 'Política', NULL,
                    :date, :sources, 'published', 'alta', NULL, :created_at
                )
                """
            ),
            {
                "id": article_id,
                "cluster_id": cluster_id,
                "slug": slug,
                "title": title,
                "content": f"{title} resumen.\n\nCuerpo.",
                "date": created_at,
                "sources": ",".join(sources[:2]),
                "created_at": created_at,
            },
        )


def test_fetch_published_articles_orders_by_cluster_size_within_window(
    sqlalchemy_db,
):
    now = datetime.now(timezone.utc)
    newer = (now - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    older = (now - timedelta(hours=2)).isoformat().replace("+00:00", "Z")
    _seed_published_with_cluster(
        article_id="v-small",
        cluster_id="c-small",
        slug="noticia-pequena",
        title="Pequeña",
        member_count=2,
        sources=["Hoy", "Acento"],
        created_at=newer,
    )
    _seed_published_with_cluster(
        article_id="v-big",
        cluster_id="c-big",
        slug="noticia-grande",
        title="Grande",
        member_count=5,
        sources=["Hoy", "Acento", "Diario Libre"],
        created_at=older,
    )

    rows = db.fetch_published_articles(limit=10)
    assert [row["slug"] for row in rows] == ["noticia-grande", "noticia-pequena"]
    assert rows[0]["cluster_size"] == 5
    assert rows[1]["cluster_size"] == 2


def test_fetch_published_articles_recent_outranks_older_larger_cluster(
    sqlalchemy_db,
):
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    stale = (now - timedelta(days=5)).isoformat().replace("+00:00", "Z")
    _seed_published_with_cluster(
        article_id="v-recent-small",
        cluster_id="c-recent-small",
        slug="reciente-pequena",
        title="Reciente pequeña",
        member_count=2,
        sources=["Hoy", "Acento"],
        created_at=recent,
    )
    _seed_published_with_cluster(
        article_id="v-stale-big",
        cluster_id="c-stale-big",
        slug="antigua-grande",
        title="Antigua grande",
        member_count=8,
        sources=["Hoy", "Acento", "Diario Libre", "Listín Diario"],
        created_at=stale,
    )

    rows = db.fetch_published_articles(limit=10, max_age_days=3)
    assert [row["slug"] for row in rows] == [
        "reciente-pequena",
        "antigua-grande",
    ]
    assert rows[0]["cluster_size"] == 2
    assert rows[1]["cluster_size"] == 8


def test_api_list_applies_lead_tiebreak(sqlalchemy_db, monkeypatch):
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _seed_published_with_cluster(
        article_id="v-a",
        cluster_id="c-a",
        slug="empate-a",
        title="Empate A",
        member_count=3,
        sources=["Hoy", "Acento", "Listín Diario"],
        created_at=now,
    )
    _seed_published_with_cluster(
        article_id="v-b",
        cluster_id="c-b",
        slug="empate-b",
        title="Empate B",
        member_count=3,
        sources=["Hoy", "Acento", "Diario Libre"],
        created_at=now,
    )
    monkeypatch.setattr(
        "api.routes.articles.apply_lead_tiebreak",
        lambda rows, **_kw: apply_lead_tiebreak(
            rows, pick_lead=lambda _tied: "empate-b"
        ),
    )

    client = TestClient(app)
    client.headers["Authorization"] = "Bearer test-api-key"
    res = client.get("/api/articles")
    assert res.status_code == 200
    articles = res.json()
    assert articles[0]["slug"] == "empate-b"
    assert articles[0]["clusterSize"] == 3
