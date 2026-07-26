from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import chromadb
from chromadb.utils import embedding_functions
from mcp.server.fastmcp import FastMCP

from config import (
    CHROMA_COLLECTION,
    CHROMA_PATH,
    DB_NAME,
    DEFAULT_DAYS_BACK,
    DEFAULT_QUERY_LIMIT,
    EMBED_MODEL,
    QUERY_CANDIDATE_MIN,
    QUERY_CANDIDATE_MULTIPLIER,
)
from pipeline import normalize_date

mcp = FastMCP("dominican_news_repository")


def query_db(sql: str, params: tuple) -> list[sqlite3.Row]:
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()


chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBED_MODEL
)
vector_collection = chroma_client.get_or_create_collection(
    name=CHROMA_COLLECTION, embedding_function=sentence_transformer_ef
)


def _parse_article_date(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = normalize_date(value)
    if not normalized:
        return None
    return datetime.fromisoformat(normalized.replace("Z", "+00:00"))


@mcp.tool()
def query_topic(
    topic: str,
    limit: int = DEFAULT_QUERY_LIMIT,
    days_back: int = DEFAULT_DAYS_BACK,
    source: str | None = None,
) -> str:
    """
    Semantic RAG search over Dominican news (Spanish-friendly embeddings).

    Args:
        topic: Conceptual topic or question (e.g. "reforma fiscal", "apagones").
        limit: Maximum articles to return.
        days_back: Only include articles from the last N days (by published date).
        source: Optional outlet name filter (e.g. "Acento", "Listin Diario").
    """
    limit = max(1, limit)
    days_back = max(0, days_back)
    date_threshold = datetime.now(timezone.utc) - timedelta(days=days_back)
    source_filter = source.strip() if source else None

    n_results = max(QUERY_CANDIDATE_MIN, limit * QUERY_CANDIDATE_MULTIPLIER)
    results = vector_collection.query(query_texts=[topic], n_results=n_results)

    if not results["ids"] or not results["ids"][0]:
        return f"No semantically relevant news found for topic: '{topic}'."

    ranked_ids = results["ids"][0]
    metadatas = (results.get("metadatas") or [[]])[0] or [{}] * len(ranked_ids)

    filtered_ids: list[str] = []
    for news_id, meta in zip(ranked_ids, metadatas):
        meta = meta or {}
        if source_filter and (meta.get("source") or "") != source_filter:
            continue
        article_dt = _parse_article_date(meta.get("date"))
        if article_dt is None or article_dt < date_threshold:
            continue
        filtered_ids.append(news_id)
        if len(filtered_ids) >= limit:
            break

    if not filtered_ids:
        scope = f"last {days_back} days"
        if source_filter:
            scope += f", source={source_filter}"
        return f"No semantically relevant news found for topic: '{topic}' ({scope})."

    rows = query_db(
        f"SELECT id, source, title, date, content, url FROM news WHERE id IN ({','.join(['?'] * len(filtered_ids))})",
        tuple(filtered_ids),
    )
    by_id = {row["id"]: row for row in rows}
    ordered = [by_id[i] for i in filtered_ids if i in by_id]

    if not ordered:
        return "Found semantic matches, but text was missing from the main database."

    context = f"--- RAG CONTEXT FOR TOPIC: '{topic}' ---\n\n"
    for row in ordered:
        context += f"SOURCE: {row['source']}\n"
        context += f"DATE: {row['date']}\n"
        context += f"HEADLINE: {row['title']}\n"
        context += f"URL: {row['url']}\n"
        context += f"CONTENT EXCERPT:\n{row['content'][:2500]}...\n"
        context += "-" * 40 + "\n\n"

    return context


if __name__ == "__main__":
    print("Starting MCP server...")
    mcp.run()
