"""Public article endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth import require_api_key
from api.mappers import (
    article_to_slug,
    is_valid_slug,
    row_to_article,
)
from api.schemas import Article, ArticleSlug
from common.db import fetch_published_article_by_slug, fetch_published_articles
from common.homepage_rank import apply_lead_tiebreak
from common.taxonomy import category_name

router = APIRouter(
    prefix="/api/articles",
    tags=["articles"],
    dependencies=[Depends(require_api_key)],
)

@router.get("", response_model=list[Article])
def list_articles(category: str | None = Query(default=None)) -> list[Article]:
    category_label = category_name(category) if category else None
    if category and category_label is None:
        return []
    rows = fetch_published_articles(limit=100, category=category_label)
    # Lead LLM tiebreak only for the default homepage feed (no category).
    if category_label is None:
        rows = apply_lead_tiebreak(rows)
    return [row_to_article(row) for row in rows]


@router.get("/slugs", response_model=list[ArticleSlug])
def list_article_slugs() -> list[ArticleSlug]:
    articles = [row_to_article(row) for row in fetch_published_articles(limit=1000)]
    return [article_to_slug(article) for article in articles]


@router.get("/{slug}", response_model=Article)
def get_article(slug: str) -> Article:
    if not is_valid_slug(slug):
        raise HTTPException(status_code=404, detail="Article not found")
    row = fetch_published_article_by_slug(slug)
    if row is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return row_to_article(row)
