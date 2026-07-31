"""Public website API: mock fixtures vs DB published articles."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import common.db as db
from api.app import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_mode(monkeypatch):
    monkeypatch.setenv("API_USE_DB", "false")


@pytest.fixture
def db_mode(sqlalchemy_db, monkeypatch):
    monkeypatch.setenv("API_USE_DB", "true")
    monkeypatch.setattr(db, "index_verified_article", lambda **_k: None)
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


def test_mock_list_and_detail(client, mock_mode):
    res = client.get("/api/articles")
    assert res.status_code == 200
    articles = res.json()
    assert len(articles) >= 7
    slugs = {a["slug"] for a in articles}
    assert "reforma-presupuesto" in slugs

    detail = client.get("/api/articles/reforma-presupuesto")
    assert detail.status_code == 200
    body = detail.json()
    assert body["title"].startswith("El Congreso")
    assert body["confidence"] == "alta"
    assert body["sources"]


def test_mock_unknown_slug(client, mock_mode):
    res = client.get("/api/articles/no-existe")
    assert res.status_code == 404


def test_db_list_excludes_drafts(client, db_mode):
    res = client.get("/api/articles")
    assert res.status_code == 200
    articles = res.json()
    slugs = {a["slug"] for a in articles}
    assert slugs == {"noticia-publicada"}


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


def test_db_detail_draft_is_404(client, db_mode):
    res = client.get("/api/articles/noticia-borrador")
    assert res.status_code == 404


def test_db_unknown_slug(client, db_mode):
    res = client.get("/api/articles/missing-slug")
    assert res.status_code == 404


def test_invalid_slug_rejected(client, mock_mode):
    res = client.get("/api/articles/Bad_Slug!")
    assert res.status_code == 404
