"""Shared helpers for MCP query tools (DB, date parsing, formatting)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from common.config import DB_NAME
from common.indexing import RetrievedChunk, RetrievedStory
from common.sources import NewsSource
from ingestion.pipeline import normalize_date


def query_db(sql: str, params: tuple) -> list[sqlite3.Row]:
    # Read-only URI so the MCP query path cannot write even if a bug appears later.
    with sqlite3.connect(f"file:{DB_NAME}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()


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


def format_story_context(
    query: str,
    stories: list[tuple[RetrievedStory, list[dict]]],
) -> str:
    context = f"--- STORY SEARCH FOR QUERY: '{query}' ---\n\n"
    for story, articles in stories:
        context += f"--- STORY: {story.description} ---\n"
        context += f"STORY_ID: {story.cluster_id}\n"
        context += f"CREATED: {story.created_at}\n"
        context += f"ARTICLES: {len(articles)}\n\n"
        for article in articles:
            context += f"  SOURCE: {article.get('source') or ''}\n"
            context += f"  DATE: {article.get('date') or ''}\n"
            context += f"  HEADLINE: {article.get('title') or ''}\n"
            context += f"  URL: {article.get('url') or ''}\n"
            context += f"  CONTENT:\n{article.get('content') or ''}\n"
            context += "  " + "-" * 38 + "\n\n"
        context += "-" * 40 + "\n\n"
    return context


def load_source_articles(
    source: NewsSource, *, days_back: int = 1
) -> list[sqlite3.Row]:
    threshold = datetime.now(timezone.utc) - timedelta(days=max(0, days_back))
    return query_db(
        """
        SELECT id, source, title, date, content, url
        FROM raw_articles
        WHERE source = ? AND date >= ?
        ORDER BY date DESC
        """,
        (source.value, threshold.isoformat()),
    )


def format_frontpage(
    source: NewsSource, rows: list[sqlite3.Row], *, days_back: int = 1
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
