"""Shared helpers for MCP query tools (DB, date parsing, formatting)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from common.db import fetch_source_articles
from common.indexing import RetrievedChunk, RetrievedStory, RetrievedVerified
from common.sources import NewsSource
from ingestion.pipeline import normalize_date


def parse_article_date(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = normalize_date(value)
    if not normalized:
        return None
    return datetime.fromisoformat(normalized.replace("Z", "+00:00"))


def filter_ranked_chunks(
    chunks: list[RetrievedChunk],
    *,
    date_threshold: datetime,
    source: NewsSource | None,
    limit: int,
) -> list[RetrievedChunk]:
    """
    Apply date/source filters, then keep the best-ranked chunk per article.
    `limit` is max distinct articles.
    """
    source_filter = source.value if source else None
    seen_articles: set[str] = set()
    filtered: list[RetrievedChunk] = []
    for chunk in chunks:
        if source_filter and chunk.source != source_filter:
            continue
        article_dt = parse_article_date(chunk.date)
        if article_dt is None or article_dt < date_threshold:
            continue
        if chunk.article_id in seen_articles:
            continue
        seen_articles.add(chunk.article_id)
        filtered.append(chunk)
        if len(filtered) >= limit:
            break
    return filtered


def format_rag_context(topic: str, chunks: list[RetrievedChunk]) -> str:
    context = f"--- RAG CONTEXT FOR QUERY: '{topic}' ---\n\n"
    for chunk in chunks:
        context += f"SOURCE: {chunk.source}\n"
        context += f"DATE: {chunk.date}\n"
        context += f"HEADLINE: {chunk.title}\n"
        context += f"URL: {chunk.url}\n"
        context += f"CHUNK:\n{chunk.text}\n"
        context += "-" * 40 + "\n\n"
    return context


def _article_matches_filters(
    article: dict,
    *,
    date_threshold: datetime,
    source_filter: str | None,
) -> bool:
    if source_filter and article.get("source") != source_filter:
        return False
    article_dt = parse_article_date(article.get("date"))
    if article_dt is None or article_dt < date_threshold:
        return False
    return True


def filter_ranked_stories(
    stories: list[RetrievedStory],
    *,
    fetch_articles,
    date_threshold: datetime,
    source: NewsSource | None,
    limit: int,
) -> list[tuple[RetrievedStory, list[dict]]]:
    """Keep top-ranked stories whose member articles pass date/source filters."""
    source_filter = source.value if source else None
    filtered: list[tuple[RetrievedStory, list[dict]]] = []
    for story in stories:
        articles = fetch_articles(story.cluster_id)
        if not any(
            _article_matches_filters(
                article,
                date_threshold=date_threshold,
                source_filter=source_filter,
            )
            for article in articles
        ):
            continue
        filtered.append((story, articles))
        if len(filtered) >= limit:
            break
    return filtered


def format_story_detail(
    cluster_id: str,
    description: str,
    created_at: str,
    articles: list[dict],
) -> str:
    """Full story block: metadata + member articles with content."""
    block = f"--- STORY: {description or ''} ---\n"
    block += f"STORY_ID: {cluster_id}\n"
    block += f"CREATED: {created_at or ''}\n"
    block += f"ARTICLES: {len(articles)}\n\n"
    for article in articles:
        block += f"  SOURCE: {article.get('source') or ''}\n"
        block += f"  DATE: {article.get('date') or ''}\n"
        block += f"  HEADLINE: {article.get('title') or ''}\n"
        block += f"  URL: {article.get('url') or ''}\n"
        block += f"  CONTENT:\n{article.get('content') or ''}\n"
        block += "  " + "-" * 38 + "\n\n"
    block += "-" * 40 + "\n\n"
    return block


def format_story_context(
    query: str,
    stories: list[tuple[RetrievedStory, list[dict]]],
) -> str:
    context = f"--- STORY SEARCH FOR QUERY: '{query}' ---\n\n"
    for story, articles in stories:
        context += format_story_detail(
            story.cluster_id,
            story.description,
            story.created_at,
            articles,
        )
    return context


def format_story_list(
    stories: list[tuple[dict, list[dict]]],
    *,
    days_back: int,
) -> str:
    """Compact story browse: description, sources, and member headlines."""
    day_label = "day" if days_back == 1 else "days"
    context = f"--- STORY LIST (last {days_back} {day_label}) ---\n\n"
    for cluster, articles in stories:
        sources = sorted(
            {
                (article.get("source") or "").strip()
                for article in articles
                if (article.get("source") or "").strip()
            }
        )
        context += f"--- STORY: {cluster.get('description') or ''} ---\n"
        context += f"STORY_ID: {cluster.get('cluster_id') or ''}\n"
        context += f"CREATED: {cluster.get('created_at') or ''}\n"
        context += f"ARTICLES: {len(articles)}\n"
        context += f"SOURCES: {', '.join(sources)}\n\n"
        for article in articles:
            context += f"  SOURCE: {article.get('source') or ''}\n"
            context += f"  HEADLINE: {article.get('title') or ''}\n"
            context += "  " + "-" * 38 + "\n"
        context += "\n" + "-" * 40 + "\n\n"
    return context


def load_source_articles(
    source: NewsSource, *, days_back: int = 1
) -> list[dict[str, Any]]:
    threshold = datetime.now(timezone.utc) - timedelta(days=max(0, days_back))
    return fetch_source_articles(source.value, threshold.isoformat())


def format_frontpage(
    source: NewsSource, rows: list[dict[str, Any]], *, days_back: int = 1
) -> str:
    day_label = "day" if days_back == 1 else "days"
    header = f"--- FRONTPAGE: {source.value} (last {days_back} {day_label}) ---\n\n"
    body = ""
    for row in rows:
        body += f"SOURCE: {row['source']}\n"
        body += f"DATE: {row['date']}\n"
        body += f"HEADLINE: {row['title']}\n"
        body += f"URL: {row['url']}\n"
        body += f"CONTENT:\n{row['content']}\n"
        body += "-" * 40 + "\n\n"
    return header + body


def _append_confidence_fields(block: str, article: dict[str, Any]) -> str:
    confidence = article.get("confidence")
    if confidence is not None and str(confidence).strip():
        block += f"CONFIDENCE: {confidence}\n"
    score = article.get("confidence_score")
    if score is not None:
        block += f"CONFIDENCE_SCORE: {score}\n"
    return block


def format_verified_detail(article: dict[str, Any]) -> str:
    """Full verified article: metadata + body."""
    block = f"--- VERIFIED: {article.get('title') or ''} ---\n"
    block += f"CLUSTER_ID: {article.get('cluster_id') or ''}\n"
    block += f"SLUG: {article.get('slug') or ''}\n"
    block += f"DATE: {article.get('date') or ''}\n"
    block += f"STATUS: {article.get('status') or ''}\n"
    block = _append_confidence_fields(block, article)
    block += f"SOURCES: {article.get('sources') or ''}\n"
    block += f"CONTENT:\n{article.get('content') or ''}\n"
    block += "-" * 40 + "\n\n"
    return block


def format_verified_list(
    articles: list[dict[str, Any]],
    *,
    days_back: int,
) -> str:
    """Compact verified browse: title, date, status, confidence, ids."""
    day_label = "day" if days_back == 1 else "days"
    context = f"--- VERIFIED LIST (last {days_back} {day_label}) ---\n\n"
    for article in articles:
        context += f"--- VERIFIED: {article.get('title') or ''} ---\n"
        context += f"CLUSTER_ID: {article.get('cluster_id') or ''}\n"
        context += f"SLUG: {article.get('slug') or ''}\n"
        context += f"DATE: {article.get('date') or ''}\n"
        context += f"STATUS: {article.get('status') or ''}\n"
        context = _append_confidence_fields(context, article)
        context += "\n" + "-" * 40 + "\n\n"
    return context


def filter_ranked_verified(
    hits: list[RetrievedVerified],
    *,
    fetch_article,
    date_threshold: datetime,
    status: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    """Hydrate Chroma hits from DB and apply date/status filters."""
    filtered: list[dict[str, Any]] = []
    for hit in hits:
        article = fetch_article(hit.cluster_id)
        if article is None:
            continue
        if status and (article.get("status") or "") != status:
            continue
        article_dt = parse_article_date(article.get("date") or article.get("created_at"))
        if article_dt is None or article_dt < date_threshold:
            continue
        filtered.append(article)
        if len(filtered) >= limit:
            break
    return filtered


def format_verified_search(query: str, articles: list[dict[str, Any]]) -> str:
    context = f"--- VERIFIED SEARCH FOR QUERY: '{query}' ---\n\n"
    for article in articles:
        context += format_verified_detail(article)
    return context
