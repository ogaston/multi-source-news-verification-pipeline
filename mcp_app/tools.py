"""MCP tool implementations (logic only; decorators live in mcp_app.server)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from common.config import (
    DEFAULT_DAYS_BACK,
    DEFAULT_QUERY_LIMIT,
    MAX_DAYS_BACK,
    MAX_QUERY_LIMIT,
    MAX_TOPIC_LENGTH,
    QUERY_CANDIDATE_MIN,
    QUERY_CANDIDATE_MULTIPLIER,
)
from common.indexing import retrieve_chunks
from common.sources import NewsSource
from mcp_app.utils import filter_ranked_chunks, format_rag_context


def run_query_topic(
    topic: str,
    limit: int = DEFAULT_QUERY_LIMIT,
    days_back: int = DEFAULT_DAYS_BACK,
    source: NewsSource | None = None,
) -> str:
    topic = (topic or "")[:MAX_TOPIC_LENGTH]
    limit = min(MAX_QUERY_LIMIT, max(1, limit))
    days_back = min(MAX_DAYS_BACK, max(0, days_back))
    date_threshold = datetime.now(timezone.utc) - timedelta(days=days_back)

    n_results = max(QUERY_CANDIDATE_MIN, limit * QUERY_CANDIDATE_MULTIPLIER)
    chunks = retrieve_chunks(topic, n_results=n_results)

    if not chunks:
        return f"No semantically relevant news found for topic: '{topic}'."

    filtered = filter_ranked_chunks(
        chunks,
        date_threshold=date_threshold,
        source=source,
        limit=limit,
    )

    if not filtered:
        scope = f"last {days_back} days"
        if source:
            scope += f", source={source.value}"
        return f"No semantically relevant news found for topic: '{topic}' ({scope})."

    return format_rag_context(topic, filtered)
