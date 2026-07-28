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
from common.sources import NewsSource
from mcp_app.utils import (
    filter_ranked_ids,
    format_rag_context,
    get_vector_collection,
    load_ordered_rows,
)


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
    results = get_vector_collection().query(query_texts=[topic], n_results=n_results)

    if not results["ids"] or not results["ids"][0]:
        return f"No semantically relevant news found for topic: '{topic}'."

    ranked_ids = results["ids"][0]
    metadatas = (results.get("metadatas") or [[]])[0] or [{}] * len(ranked_ids)

    filtered_ids = filter_ranked_ids(
        ranked_ids,
        metadatas,
        date_threshold=date_threshold,
        source=source,
        limit=limit,
    )

    if not filtered_ids:
        scope = f"last {days_back} days"
        if source:
            scope += f", source={source.value}"
        return f"No semantically relevant news found for topic: '{topic}' ({scope})."

    ordered = load_ordered_rows(filtered_ids)
    if not ordered:
        return "Found semantic matches, but text was missing from the main database."

    return format_rag_context(topic, ordered)
