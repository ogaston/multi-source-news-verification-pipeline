"""MCP tool implementations (logic only; decorators live in mcp_app.server)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import TypeVar

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

_Retrieved = TypeVar("_Retrieved")
_Filtered = TypeVar("_Filtered")


def _clamp_limit(limit: int) -> int:
    return min(MAX_QUERY_LIMIT, max(1, limit))


def _clamp_days_back(days_back: int) -> int:
    return min(MAX_DAYS_BACK, max(0, days_back))


def _date_threshold(days_back: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_back)


def _run_semantic_search(
    *,
    query: str,
    limit: int,
    days_back: int,
    result_label: str,
    retrieve: Callable[[str, int], list[_Retrieved]],
    filter_results: Callable[
        [list[_Retrieved], datetime, int], list[_Filtered]
    ],
    format_results: Callable[[str, list[_Filtered]], str],
    scope_filter: str | None = None,
) -> str:
    query = (query or "")[:MAX_TOPIC_LENGTH]
    limit = _clamp_limit(limit)
    days_back = _clamp_days_back(days_back)
    threshold = _date_threshold(days_back)
    n_results = max(QUERY_CANDIDATE_MIN, limit * QUERY_CANDIDATE_MULTIPLIER)
    results = retrieve(query, n_results)

    if not results:
        return f"No semantically relevant {result_label} found for query: '{query}'."

    filtered = filter_results(results, threshold, limit)
    if not filtered:
        scope = f"last {days_back} days"
        if scope_filter:
            scope += f", {scope_filter}"
        return (
            f"No semantically relevant {result_label} found for query: "
            f"'{query}' ({scope})."
        )

    return format_results(query, filtered)


def run_search_articles(
    query: str,
    limit: int = DEFAULT_QUERY_LIMIT,
    days_back: int = DEFAULT_DAYS_BACK,
    source: NewsSource | None = None,
) -> str:
    return _run_semantic_search(
        query=query,
        limit=limit,
        days_back=days_back,
        result_label="news",
        retrieve=retrieve_chunks,
        filter_results=lambda chunks, threshold, result_limit: filter_ranked_chunks(
            chunks,
            date_threshold=threshold,
            source=source,
            limit=result_limit,
        ),
        format_results=format_rag_context,
        scope_filter=f"source={source.value}" if source else None,
    )


def run_search_story(
    query: str,
    limit: int = DEFAULT_QUERY_LIMIT,
    days_back: int = DEFAULT_DAYS_BACK,
    source: NewsSource | None = None,
) -> str:
    return _run_semantic_search(
        query=query,
        limit=limit,
        days_back=days_back,
        result_label="stories",
        retrieve=retrieve_stories,
        filter_results=lambda stories, threshold, result_limit: filter_ranked_stories(
            stories,
            fetch_articles=fetch_cluster_articles,
            date_threshold=threshold,
            source=source,
            limit=result_limit,
        ),
        format_results=format_story_context,
        scope_filter=f"source={source.value}" if source else None,
    )


def run_list_stories(
    days_back: int = DEFAULT_LIST_DAYS_BACK,
    limit: int = DEFAULT_LIST_STORIES_LIMIT,
    source: NewsSource | None = None,
) -> str:
    limit = _clamp_limit(limit)
    days_back = _clamp_days_back(days_back)
    date_threshold = _date_threshold(days_back)

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
    limit = _clamp_limit(limit)
    days_back = _clamp_days_back(days_back)
    date_threshold = _date_threshold(days_back)
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
    status = (status or "").strip() or None
    return _run_semantic_search(
        query=query,
        limit=limit,
        days_back=days_back,
        result_label="verified articles",
        retrieve=retrieve_verified,
        filter_results=lambda hits, threshold, result_limit: filter_ranked_verified(
            hits,
            fetch_article=fetch_verified_article,
            date_threshold=threshold,
            status=status,
            limit=result_limit,
        ),
        format_results=format_verified_search,
        scope_filter=f"status={status}" if status else None,
    )
