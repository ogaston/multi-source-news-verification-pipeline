"""Public website API backed by published PostgreSQL articles."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import common.db as db
from api.app import app


@pytest.fixture
def client():
    api_client = TestClient(app)
    api_client.headers["Authorization"] = "Bearer test-api-key"
    return api_client


@pytest.fixture
def db_mode(sqlalchemy_db):
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(hours=1)).isoformat()
    with db.get_engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO verified_articles (
                    id, cluster_id, slug, title, content, category, image_url,
                    date, sources, status, confidence, confidence_score, created_at
                )
                VALUES (
                    :id, :cluster_id, :slug, :title, :content, :category, NULL,
                    :date, :sources, :status, :confidence, NULL, :created_at
                )
                """
            ),
            [
                {
                    "id": "pub1",
                    "cluster_id": "c-pub",
                    "slug": "noticia-publicada",
                    "title": "Noticia publicada",
                    "content": (
                        "Primer párrafo de resumen.\n\n"
                        "Segundo párrafo del cuerpo."
                    ),
                    "category": "Política",
                    "date": recent,
                    "sources": "Diario Libre, Hoy",
                    "status": "published",
                    "confidence": "alta",
                    "created_at": recent,
                },
                {
                    "id": "draft1",
                    "cluster_id": "c-draft",
                    "slug": "noticia-borrador",
                    "title": "Noticia borrador",
                    "content": "No debe aparecer.",
                    "category": "Sociedad",
                    "date": recent,
                    "sources": "Hoy",
                    "status": "draft",
                    "confidence": "media",
                    "created_at": recent,
                },
            ],
        )
    return sqlalchemy_db


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_articles_require_api_key():
    unauthenticated = TestClient(app)
    missing = unauthenticated.get("/api/articles")
    wrong = unauthenticated.get(
        "/api/articles",
        headers={"Authorization": "Bearer wrong-key"},
    )

    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
    assert wrong.status_code == 401
    assert unauthenticated.get("/health").status_code == 200


def test_db_list_excludes_drafts(client, db_mode, monkeypatch):
    monkeypatch.setattr(
        "api.routes.articles.apply_lead_tiebreak",
        lambda rows, **_kw: list(rows),
    )
    res = client.get("/api/articles")
    assert res.status_code == 200
    articles = res.json()
    slugs = {a["slug"] for a in articles}
    assert slugs == {"noticia-publicada"}
    assert articles[0].get("clusterSize") == 0


def test_db_detail_published(client, db_mode):
    res = client.get("/api/articles/noticia-publicada")
    assert res.status_code == 200
    body = res.json()
    assert body["category"] == "Política"
    assert body["confidence"] == "alta"
    assert body["summary"].startswith("Primer párrafo")
    assert "Segundo párrafo" in body["body"][0] or len(body["body"]) >= 1
    names = {s["name"] for s in body["sources"]}
    assert "Diario Libre" in names
    assert "Hoy" in names
    assert body["publishedAt"].endswith("Z")


def test_db_category_and_slugs_exclude_drafts(client, db_mode):
    category = client.get("/api/articles?category=politica")
    assert [article["slug"] for article in category.json()] == [
        "noticia-publicada"
    ]
    assert client.get("/api/articles?category=no-existe").json() == []

    slugs = client.get("/api/articles/slugs").json()
    assert [item["slug"] for item in slugs] == ["noticia-publicada"]
    assert slugs[0]["categorySlug"] == "politica"
    assert slugs[0]["publishedAt"].endswith("Z")


def test_db_detail_draft_is_404(client, db_mode):
    res = client.get("/api/articles/noticia-borrador")
    assert res.status_code == 404


def test_db_unknown_slug(client, db_mode):
    res = client.get("/api/articles/missing-slug")
    assert res.status_code == 404


def test_invalid_slug_rejected(client):
    res = client.get("/api/articles/Bad_Slug!")
    assert res.status_code == 404
