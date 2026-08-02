"""Tests for public API row mappers."""

from __future__ import annotations

from api.mappers import _parse_sources, row_to_article
from common.sources import source_url
from common.taxonomy import ALLOWED_CATEGORIES, category_name, category_slug


def test_website_categories_round_trip():
    assert {
        category_slug(category): category for category in ALLOWED_CATEGORIES
    } == {
        "politica": "Política",
        "economia": "Economía",
        "clima": "Clima",
        "tecnologia": "Tecnología",
        "sociedad": "Sociedad",
        "cultura": "Cultura",
    }
    assert all(
        category_name(category_slug(category)) == category
        for category in ALLOWED_CATEGORIES
    )


def test_source_url_preserves_listin_aliases():
    assert source_url("Listín Diario") == "https://listindiario.com"
    assert source_url("Listin Diario") == "https://listindiario.com"


def test_parse_sources_json_article_urls():
    raw = (
        '[{"name":"Hoy","url":"https://hoy.com.do/nota-1"},'
        '{"name":"Diario Libre","url":"https://www.diariolibre.com/nota-2"}]'
    )
    sources = _parse_sources(raw)
    assert [s.name for s in sources] == ["Hoy", "Diario Libre"]
    assert sources[0].url == "https://hoy.com.do/nota-1"
    assert sources[1].url == "https://www.diariolibre.com/nota-2"


def test_parse_sources_legacy_csv_uses_homepage_map():
    sources = _parse_sources("Diario Libre, Hoy")
    assert [s.name for s in sources] == ["Diario Libre", "Hoy"]
    assert sources[0].url == "https://www.diariolibre.com"
    assert sources[1].url == "https://hoy.com.do"


def test_parse_sources_json_missing_url_falls_back_to_homepage():
    sources = _parse_sources('[{"name":"Hoy","url":""}]')
    assert len(sources) == 1
    assert sources[0].url == "https://hoy.com.do"


def test_row_to_article_uses_json_sources():
    article = row_to_article(
        {
            "slug": "nota-1",
            "category": "Política",
            "title": "Titular",
            "content": "Resumen.\n\nCuerpo.",
            "image_url": None,
            "confidence": "alta",
            "sources": '[{"name":"Hoy","url":"https://hoy.com.do/a"}]',
            "date": "2026-07-31",
            "created_at": "2026-07-31T12:00:00Z",
            "cluster_size": 7,
        }
    )
    assert article.sources[0].url == "https://hoy.com.do/a"
    assert article.clusterSize == 7
