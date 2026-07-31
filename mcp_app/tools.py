"""MCP tool implementations (logic only; decorators live in mcp_app.server)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from common.config import (
    DEFAULT_DAYS_BACK,
    DEFAULT_LIST_DAYS_BACK,
    DEFAULT_LIST_STORIES_LIMIT,
    DEFAULT_QUERY_LIMIT,
    MAX_DAYS_BACK,
    MAX_QUERY_LIMIT,
    MAX_TOPIC_LENGTH,
    QUERY_CANDIDATE_MIN,
    QUERY_CANDIDATE_MULTIPLIER,
)
from common.db import (
    fetch_cluster,
    fetch_cluster_articles,
    fetch_recent_clusters,
    fetch_verified_article,
    fetch_verified_articles,
)
from common.indexing import retrieve_chunks, retrieve_stories, retrieve_verified
from common.sources import NewsSource
from mcp_app.utils import (
    filter_ranked_chunks,
    filter_ranked_stories,
    filter_ranked_verified,
    format_rag_context,
    format_story_context,
    format_story_detail,
    format_story_list,
    format_verified_detail,
    format_verified_list,
    format_verified_search,
)


def run_search_articles(
    query: str,
    limit: int = DEFAULT_QUERY_LIMIT,
    days_back: int = DEFAULT_DAYS_BACK,
    source: NewsSource | None = None,
) -> str:
    query = (query or "")[:MAX_TOPIC_LENGTH]
    limit = min(MAX_QUERY_LIMIT, max(1, limit))
    days_back = min(MAX_DAYS_BACK, max(0, days_back))
    date_threshold = datetime.now(timezone.utc) - timedelta(days=days_back)

    n_results = max(QUERY_CANDIDATE_MIN, limit * QUERY_CANDIDATE_MULTIPLIER)
    chunks = retrieve_chunks(query, n_results=n_results)

    if not chunks:
        return f"No semantically relevant news found for query: '{query}'."

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
        return f"No semantically relevant news found for query: '{query}' ({scope})."

    return format_rag_context(query, filtered)


def run_search_story(
    query: str,
    limit: int = DEFAULT_QUERY_LIMIT,
    days_back: int = DEFAULT_DAYS_BACK,
    source: NewsSource | None = None,
) -> str:
    query = (query or "")[:MAX_TOPIC_LENGTH]
    limit = min(MAX_QUERY_LIMIT, max(1, limit))
    days_back = min(MAX_DAYS_BACK, max(0, days_back))
    date_threshold = datetime.now(timezone.utc) - timedelta(days=days_back)

    n_results = max(QUERY_CANDIDATE_MIN, limit * QUERY_CANDIDATE_MULTIPLIER)
    stories = retrieve_stories(query, n_results=n_results)

    if not stories:
        return f"No semantically relevant stories found for query: '{query}'."

    filtered = filter_ranked_stories(
        stories,
        fetch_articles=fetch_cluster_articles,
        date_threshold=date_threshold,
        source=source,
        limit=limit,
    )

    if not filtered:
        scope = f"last {days_back} days"
        if source:
            scope += f", source={source.value}"
        return f"No semantically relevant stories found for query: '{query}' ({scope})."

    return format_story_context(query, filtered)


def run_list_stories(
    days_back: int = DEFAULT_LIST_DAYS_BACK,
    limit: int = DEFAULT_LIST_STORIES_LIMIT,
    source: NewsSource | None = None,
) -> str:
    limit = min(MAX_QUERY_LIMIT, max(1, limit))
    days_back = min(MAX_DAYS_BACK, max(0, days_back))
    date_threshold = datetime.now(timezone.utc) - timedelta(days=days_back)

    clusters = fetch_recent_clusters(
        date_threshold.isoformat(),
        source=source.value if source else None,
        limit=limit,
    )
    if not clusters:
        day_label = "day" if days_back == 1 else "days"
        scope = f"last {days_back} {day_label}"
        if source:
            scope += f", source={source.value}"
        return f"No stories found ({scope})."

    stories = [
        (cluster, fetch_cluster_articles(cluster["cluster_id"]))
        for cluster in clusters
    ]
    return format_story_list(stories, days_back=days_back)


def run_get_story(story_id: str) -> str:
    story_id = (story_id or "").strip()
    if not story_id:
        return "Story not found: missing story_id."

    cluster = fetch_cluster(story_id)
    if cluster is None:
        return f"Story not found: '{story_id}'."

    articles = fetch_cluster_articles(story_id)
    return format_story_detail(
        cluster["cluster_id"],
        cluster.get("description") or "",
        cluster.get("created_at") or "",
        articles,
    )


def run_list_verified_articles(
    days_back: int = DEFAULT_LIST_DAYS_BACK,
    limit: int = DEFAULT_LIST_STORIES_LIMIT,
    status: str | None = None,
) -> str:
    limit = min(MAX_QUERY_LIMIT, max(1, limit))
    days_back = min(MAX_DAYS_BACK, max(0, days_back))
    date_threshold = datetime.now(timezone.utc) - timedelta(days=days_back)
    status = (status or "").strip() or None

    articles = fetch_verified_articles(
        date_threshold.isoformat(),
        status=status,
        limit=limit,
    )
    if not articles:
        day_label = "day" if days_back == 1 else "days"
        scope = f"last {days_back} {day_label}"
        if status:
            scope += f", status={status}"
        return f"No verified articles found ({scope})."

    return format_verified_list(articles, days_back=days_back)


def run_get_verified_article(cluster_id: str) -> str:
    cluster_id = (cluster_id or "").strip()
    if not cluster_id:
        return "Verified article not found: missing cluster_id."

    article = fetch_verified_article(cluster_id)
    if article is None:
        return f"Verified article not found: '{cluster_id}'."

    return format_verified_detail(article)


def run_search_verified_articles(
    query: str,
    limit: int = DEFAULT_QUERY_LIMIT,
    days_back: int = DEFAULT_DAYS_BACK,
    status: str | None = None,
) -> str:
    query = (query or "")[:MAX_TOPIC_LENGTH]
    limit = min(MAX_QUERY_LIMIT, max(1, limit))
    days_back = min(MAX_DAYS_BACK, max(0, days_back))
    date_threshold = datetime.now(timezone.utc) - timedelta(days=days_back)
    status = (status or "").strip() or None

    n_results = max(QUERY_CANDIDATE_MIN, limit * QUERY_CANDIDATE_MULTIPLIER)
    hits = retrieve_verified(query, n_results=n_results)

    if not hits:
        return f"No semantically relevant verified articles found for query: '{query}'."

    filtered = filter_ranked_verified(
        hits,
        fetch_article=fetch_verified_article,
        date_threshold=date_threshold,
        status=status,
        limit=limit,
    )

    if not filtered:
        scope = f"last {days_back} days"
        if status:
            scope += f", status={status}"
        return (
            f"No semantically relevant verified articles found for query: "
            f"'{query}' ({scope})."
        )

    return format_verified_search(query, filtered)
