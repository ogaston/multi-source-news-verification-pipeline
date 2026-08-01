"""Public article endpoints."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Query

from api.mappers import (
    article_to_slug,
    category_name,
    category_slug,
    is_valid_slug,
    row_to_article,
)
from api.mock_articles import get_mock_article, list_mock_articles
from api.schemas import Article, ArticleSlug
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
def list_articles(category: str | None = Query(default=None)) -> list[Article]:
    category_label = category_name(category) if category else None
    if category and category_label is None:
        return []
    if not _use_db():
        articles = list_mock_articles()
        if category:
            articles = [
                article
                for article in articles
                if category_slug(article.category) == category
            ]
        return articles
    rows = fetch_published_articles(limit=100, category=category_label)
    return [row_to_article(row) for row in rows]


@router.get("/slugs", response_model=list[ArticleSlug])
def list_article_slugs() -> list[ArticleSlug]:
    if not _use_db():
        articles = list_mock_articles()
    else:
        articles = [
            row_to_article(row) for row in fetch_published_articles(limit=1000)
        ]
    return [article_to_slug(article) for article in articles]


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
