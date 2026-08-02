"""Tests for MCP resource logic (sources catalog + frontpage)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

import common.db as db
import mcp_app.resources as resources
from common.sources import NewsSource
from mcp_app.resources import (
    get_source_frontpage,
    get_verified_resource,
    list_sources_json,
    resolve_source_id,
)
from tests.conftest import insert_raw_articles


@pytest.fixture
def frontpage_db(sqlalchemy_db):
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(hours=6)).isoformat()
    older = (now - timedelta(days=3)).isoformat()

    insert_raw_articles(
        [
            {
                "id": "acento-recent",
                "source": "Acento",
                "title": "Recent Acento",
                "date": recent,
                "content": "Acento body",
                "url": "https://example.com/acento-recent",
                "processed": 0,
            },
            {
                "id": "acento-old",
                "source": "Acento",
                "title": "Old Acento",
                "date": older,
                "content": "Old body",
                "url": "https://example.com/acento-old",
                "processed": 0,
            },
            {
                "id": "hoy-recent",
                "source": "Hoy",
                "title": "Recent Hoy",
                "date": recent,
                "content": "Hoy body",
                "url": "https://example.com/hoy-recent",
                "processed": 0,
            },
        ]
    )
    return sqlalchemy_db


class TestListSourcesJson:
    def test_includes_all_news_sources(self):
        items = list_sources_json()
        assert len(items) == len(NewsSource)
        by_id = {item["id"]: item["name"] for item in items}
        for member in NewsSource:
            assert by_id[member.name.lower()] == member.value


class TestResolveSourceId:
    def test_resolves_lowercase_enum_name(self):
        assert resolve_source_id("acento") is NewsSource.ACENTO
        assert resolve_source_id("listin_diario") is NewsSource.LISTIN_DIARIO

    def test_unknown_returns_none(self):
        assert resolve_source_id("unknown_outlet") is None


class TestGetSourceFrontpage:
    def test_unknown_source_id(self):
        text = get_source_frontpage("not_a_source")
        assert "Unknown source_id" in text
        assert "acento" in text

    def test_includes_only_last_day_for_source(self, frontpage_db):
        text = get_source_frontpage("acento")
        assert "FRONTPAGE: Acento" in text
        assert "Recent Acento" in text
        assert "Acento body" in text
        assert "Old Acento" not in text
        assert "Recent Hoy" not in text

    def test_empty_when_no_recent_articles(self, frontpage_db):
        text = get_source_frontpage("diario_libre")
        assert text == "No articles found for Diario Libre in the last 1 day."


class TestGetVerifiedResource:
    def test_delegates_to_verified_article_tool(self, monkeypatch):
        monkeypatch.setattr(
            resources,
            "run_get_verified_article",
            lambda cluster_id: f"detail:{cluster_id}",
        )
        assert get_verified_resource("cluster-1") == "detail:cluster-1"

    def test_not_found(self, sqlalchemy_db):
        assert "Verified article not found: 'missing'" in get_verified_resource(
            "missing"
        )

    def test_returns_detail(self, sqlalchemy_db):
        now = datetime.now(timezone.utc).isoformat()
        with db.get_engine().begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO verified_articles (
                        id, cluster_id, slug, title, content, date, sources,
                        status, created_at
                    )
                    VALUES (
                        'vr1', 'c-vr', 'slug-vr', 'Titulo VR', 'Cuerpo VR',
                        :date, 'Hoy', 'draft', :date
                    )
                    """
                ),
                {"date": now},
            )
        text_out = get_verified_resource("c-vr")
        assert "VERIFIED: Titulo VR" in text_out
        assert "CONTENT:\nCuerpo VR" in text_out
