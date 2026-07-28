"""Shared helpers for MCP query tools (DB, Chroma, date parsing, formatting)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from common.config import CHROMA_COLLECTION, CHROMA_PATH, DB_NAME, EMBED_MODEL
from common.sources import NewsSource
from ingestion.pipeline import normalize_date

_vector_collection = None


def query_db(sql: str, params: tuple) -> list[sqlite3.Row]:
    # Read-only URI so the MCP query path cannot write even if a bug appears later.
    with sqlite3.connect(f"file:{DB_NAME}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()


def get_vector_collection():
    global _vector_collection
    if _vector_collection is None:
        import chromadb
        from chromadb.utils import embedding_functions

        client = chromadb.PersistentClient(path=CHROMA_PATH)
        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBED_MODEL
        )
        _vector_collection = client.get_or_create_collection(
            name=CHROMA_COLLECTION, embedding_function=embedding_fn
        )
    return _vector_collection


def parse_article_date(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = normalize_date(value)
    if not normalized:
        return None
    return datetime.fromisoformat(normalized.replace("Z", "+00:00"))


def filter_ranked_ids(
    ranked_ids: list[str],
    metadatas: list[dict | None],
    *,
    date_threshold: datetime,
    source: NewsSource | None,
    limit: int,
) -> list[str]:
    source_filter = source.value if source else None
    filtered_ids: list[str] = []
    for news_id, meta in zip(ranked_ids, metadatas):
        meta = meta or {}
        if source_filter and (meta.get("source") or "") != source_filter:
            continue
        article_dt = parse_article_date(meta.get("date"))
        if article_dt is None or article_dt < date_threshold:
            continue
        filtered_ids.append(news_id)
        if len(filtered_ids) >= limit:
            break
    return filtered_ids


def load_ordered_rows(filtered_ids: list[str]) -> list[sqlite3.Row]:
    rows = query_db(
        f"SELECT id, source, title, date, content, url FROM news WHERE id IN ({','.join(['?'] * len(filtered_ids))})",
        tuple(filtered_ids),
    )
    by_id = {row["id"]: row for row in rows}
    return [by_id[i] for i in filtered_ids if i in by_id]


def format_rag_context(topic: str, rows: list[sqlite3.Row]) -> str:
    context = f"--- RAG CONTEXT FOR TOPIC: '{topic}' ---\n\n"
    for row in rows:
        context += f"SOURCE: {row['source']}\n"
        context += f"DATE: {row['date']}\n"
        context += f"HEADLINE: {row['title']}\n"
        context += f"URL: {row['url']}\n"
        context += f"CONTENT EXCERPT:\n{row['content'][:2500]}...\n"
        context += "-" * 40 + "\n\n"
    return context


def load_source_articles(
    source: NewsSource, *, days_back: int = 1
) -> list[sqlite3.Row]:
    threshold = datetime.now(timezone.utc) - timedelta(days=max(0, days_back))
    return query_db(
        """
        SELECT id, source, title, date, content, url
        FROM news
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
