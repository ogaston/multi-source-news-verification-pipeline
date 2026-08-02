"""Tests for story-audit selection, sources, and persist helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

from sqlalchemy import text

import common.db as db
from audit.persist import (
    article_sources,
    attach_cover_image,
    persist_verified,
    prepend_place_dateline,
)
from audit.story_audit import run_batch
from tests.conftest import insert_raw_articles


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _seed_cluster(
    *,
    cluster_id: str,
    article_count: int,
    created_at: str,
    description: str = "Historia",
    category: str = "Política",
    place: str = "Santo Domingo",
    processed: int = 0,
    article_date: str | None = None,
) -> None:
    if article_date is None:
        article_date = datetime.now(timezone.utc).date().isoformat()
    with db.get_engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO clusters (
                    cluster_id, description, category, place, created_at, processed
                )
                VALUES (
                    :cluster_id, :description, :category, :place, :created_at, :processed
                )
                """
            ),
            {
                "cluster_id": cluster_id,
                "description": description,
                "category": category,
                "place": place,
                "created_at": created_at,
                "processed": processed,
            },
        )
    rows = []
    for i in range(article_count):
        article_id = f"{cluster_id}-a{i}"
        rows.append(
            {
                "id": article_id,
                "url": f"https://example.com/{article_id}",
                "source": f"Fuente {i % 2}",
                "title": f"Titulo {i}",
                "content": f"Contenido {i}",
                "date": article_date,
                "category": "Sociedad",
                "scraped_at": created_at,
                "processed": 1,
            }
        )
    insert_raw_articles(rows)
    with db.get_engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO topic_clusters (cluster_id, article_id, created_at)
                VALUES (:cluster_id, :article_id, :created_at)
                """
            ),
            [
                {
                    "cluster_id": cluster_id,
                    "article_id": f"{cluster_id}-a{i}",
                    "created_at": created_at,
                }
                for i in range(article_count)
            ],
        )


def test_fetch_unprocessed_clusters_orders_by_article_count(sqlalchemy_db):
    older = "2026-07-01T10:00:00Z"
    newer = "2026-07-02T10:00:00Z"
    _seed_cluster(cluster_id="small", article_count=1, created_at=older)
    _seed_cluster(cluster_id="big", article_count=4, created_at=newer)
    _seed_cluster(cluster_id="medium", article_count=2, created_at=older)

    rows = db.fetch_unprocessed_clusters(10)
    assert [row["cluster_id"] for row in rows] == ["big", "medium", "small"]
    assert rows[0]["article_count"] == 4
    assert rows[0]["category"] == "Política"
    assert rows[0]["place"] == "Santo Domingo"


def test_fetch_unprocessed_clusters_skips_stale_articles(sqlalchemy_db):
    created = _now()
    _seed_cluster(
        cluster_id="fresh",
        article_count=1,
        created_at=created,
        article_date=datetime.now(timezone.utc).date().isoformat(),
    )
    _seed_cluster(
        cluster_id="stale",
        article_count=5,
        created_at=created,
        article_date="2020-01-01",
    )

    rows = db.fetch_unprocessed_clusters(10, max_age_days=3)
    assert [row["cluster_id"] for row in rows] == ["fresh"]


def test_run_batch_processes_single_top_batch(sqlalchemy_db, monkeypatch):
    _seed_cluster(cluster_id="c1", article_count=3, created_at="2026-07-01T10:00:00Z")
    _seed_cluster(cluster_id="c2", article_count=2, created_at="2026-07-01T11:00:00Z")
    _seed_cluster(cluster_id="c3", article_count=1, created_at="2026-07-01T12:00:00Z")

    seen: list[str] = []

    def fake_audit(_app, cluster, *, save, generate_image=False):
        seen.append(cluster["cluster_id"])
        return True

    monkeypatch.setattr("audit.story_audit.build_graph", lambda: MagicMock())
    monkeypatch.setattr("audit.story_audit.audit_cluster", fake_audit)
    monkeypatch.setattr("audit.story_audit.init_db", lambda: None)

    run_batch(batch_size=2, save=True)
    assert seen == ["c1", "c2"]


def test_run_batch_limits_image_generation_to_first_nine(
    sqlalchemy_db, monkeypatch
):
    for i in range(12):
        _seed_cluster(
            cluster_id=f"img{i}",
            article_count=20 - i,
            created_at=f"2026-07-01T{10 + (i % 10):02d}:{i:02d}:00Z",
        )

    image_flags: list[bool] = []

    def fake_audit(_app, cluster, *, save, generate_image=False):
        image_flags.append(generate_image)
        return True

    monkeypatch.setattr("audit.story_audit.ARTICLE_IMAGE_MAX_PER_BATCH", 9)
    monkeypatch.setattr("audit.story_audit.build_graph", lambda: MagicMock())
    monkeypatch.setattr("audit.story_audit.audit_cluster", fake_audit)
    monkeypatch.setattr("audit.story_audit.init_db", lambda: None)

    run_batch(batch_size=12, save=True)
    assert image_flags == [True] * 9 + [False] * 3


def test_fetch_unprocessed_clusters_breaks_ties_by_source_count(sqlalchemy_db):
    created = _now()
    _seed_cluster(cluster_id="few-sources", article_count=4, created_at=created)
    # Override sources so all four members share one outlet.
    with db.get_engine().begin() as conn:
        conn.execute(
            text("UPDATE raw_articles SET source = 'Solo' WHERE id LIKE 'few-sources-%'")
        )
    _seed_cluster(cluster_id="many-sources", article_count=4, created_at=created)
    with db.get_engine().begin() as conn:
        for i in range(4):
            conn.execute(
                text(
                    "UPDATE raw_articles SET source = :source "
                    "WHERE id = :id"
                ),
                {"source": f"Outlet-{i}", "id": f"many-sources-a{i}"},
            )

    rows = db.fetch_unprocessed_clusters(10)
    assert [row["cluster_id"] for row in rows[:2]] == [
        "many-sources",
        "few-sources",
    ]
    assert rows[0]["source_count"] == 4
    assert rows[1]["source_count"] == 1


def test_attach_cover_image_updates_db(sqlalchemy_db, monkeypatch):
    monkeypatch.setattr("common.indexing.index_verified_article", lambda **_k: None)
    created = _now()
    _seed_cluster(cluster_id="cover-1", article_count=1, created_at=created)
    article_id = persist_verified(
        cluster_id="cover-1",
        result={"article": "Titular\n\nCuerpo.", "analysis": None},
        articles=db.fetch_cluster_articles("cover-1"),
    )
    monkeypatch.setattr(
        "audit.persist.generate_article_image",
        lambda **_k: "http://localhost:7002/media/articles/x.jpg",
    )
    url = attach_cover_image(
        article_id=article_id,
        title="Titular",
        category="Política",
        place="Santo Domingo",
    )
    assert url == "http://localhost:7002/media/articles/x.jpg"
    row = db.fetch_verified_article("cover-1")
    assert row is not None
    assert row["image_url"] == url


def test_attach_cover_image_soft_fails(sqlalchemy_db, monkeypatch):
    monkeypatch.setattr(
        "audit.persist.generate_article_image",
        lambda **_k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert attach_cover_image(article_id="missing", title="Titular") is None


def test_article_sources_json_with_urls():
    raw = article_sources(
        [
            {
                "source": "Hoy",
                "url": "https://hoy.com.do/a",
            },
            {
                "source": "Hoy",
                "url": "https://hoy.com.do/b",
            },
            {
                "source": "Diario Libre",
                "url": "https://www.diariolibre.com/x",
            },
        ]
    )
    assert raw is not None
    data = json.loads(raw)
    assert data == [
        {"name": "Diario Libre", "url": "https://www.diariolibre.com/x"},
        {"name": "Hoy", "url": "https://hoy.com.do/a"},
    ]


def test_prepend_place_dateline():
    assert prepend_place_dateline("Cuerpo.", "Santo Domingo") == (
        "SANTO DOMINGO.— Cuerpo."
    )
    assert prepend_place_dateline("SANTO DOMINGO.— Cuerpo.", "Santo Domingo") == (
        "SANTO DOMINGO.— Cuerpo."
    )
    assert prepend_place_dateline("Cuerpo.", None) == "Cuerpo."
    assert prepend_place_dateline("Cuerpo.", "Nacional") == "Cuerpo."


def test_persist_verified_writes_place_category_and_sources(sqlalchemy_db, monkeypatch):
    monkeypatch.setattr("common.indexing.index_verified_article", lambda **_k: None)
    created = _now()
    _seed_cluster(
        cluster_id="persist-1",
        article_count=2,
        created_at=created,
        category="Economía",
        place="Santiago",
    )
    members = db.fetch_cluster_articles("persist-1")

    article_id = persist_verified(
        cluster_id="persist-1",
        result={
            "article": "Titular verificado\n\nEl cuerpo del artículo.",
            "analysis": None,
        },
        articles=members,
        category="Economía",
        place="Santiago",
    )
    assert article_id
    row = db.fetch_verified_article("persist-1")
    assert row is not None
    assert row["category"] == "Economía"
    assert row["place"] == "SANTIAGO"
    assert row["content"].startswith("SANTIAGO.—")
    assert "El cuerpo del artículo." in row["content"]
    sources = json.loads(row["sources"])
    assert sources[0]["name"]
    assert sources[0]["url"].startswith("https://example.com/")
    cluster = db.fetch_cluster("persist-1")
    assert cluster is not None
    assert cluster["processed"] == 1


def test_persist_verified_uses_cluster_category_not_outlet_section(
    sqlalchemy_db, monkeypatch
):
    monkeypatch.setattr("common.indexing.index_verified_article", lambda **_k: None)
    created = _now()
    _seed_cluster(
        cluster_id="persist-cultura",
        article_count=1,
        created_at=created,
        category="Cultura",
        place="Santo Domingo",
    )
    with db.get_engine().begin() as conn:
        conn.execute(
            text(
                "UPDATE raw_articles SET category = :category "
                "WHERE id = :id"
            ),
            {"category": "Nacionales", "id": "persist-cultura-a0"},
        )
    members = db.fetch_cluster_articles("persist-cultura")

    persist_verified(
        cluster_id="persist-cultura",
        result={
            "article": "Titular\n\nCuerpo.",
            "analysis": None,
        },
        articles=members,
    )
    row = db.fetch_verified_article("persist-cultura")
    assert row is not None
    assert row["category"] == "Cultura"
    assert row["place"] == "SANTO DOMINGO"
