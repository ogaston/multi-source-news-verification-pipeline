"""Public article endpoints."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException

from api.mappers import is_valid_slug, row_to_article
from api.mock_articles import get_mock_article, list_mock_articles
from api.schemas import Article
from common.db import fetch_published_article_by_slug, fetch_published_articles

router = APIRouter(prefix="/api/articles", tags=["articles"])


def _use_db() -> bool:
    return os.environ.get("API_USE_DB", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


@router.get("", response_model=list[Article])
def list_articles() -> list[Article]:
    if not _use_db():
        return list_mock_articles()
    rows = fetch_published_articles(limit=100)
    return [row_to_article(row) for row in rows]


@router.get("/{slug}", response_model=Article)
def get_article(slug: str) -> Article:
    if not is_valid_slug(slug):
        raise HTTPException(status_code=404, detail="Article not found")
    if not _use_db():
        article = get_mock_article(slug)
        if article is None:
            raise HTTPException(status_code=404, detail="Article not found")
        return article
    row = fetch_published_article_by_slug(slug)
    if row is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return row_to_article(row)
