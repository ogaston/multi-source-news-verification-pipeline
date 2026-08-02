"""Process-local cache for trusted search results."""

from __future__ import annotations

import time
from threading import Lock
from typing import Any, TypeVar

SearchCacheKey = tuple[str, tuple[str, ...], int, str, str]
_SearchResult = TypeVar("_SearchResult")

_CACHE: dict[SearchCacheKey, tuple[float, tuple[Any, ...]]] = {}
_CACHE_LOCK = Lock()


def clear_search_cache() -> None:
    """Clear the process-local search cache."""

    with _CACHE_LOCK:
        _CACHE.clear()


def get_cached_search_results(
    key: SearchCacheKey, ttl_seconds: int
) -> list[_SearchResult] | None:
    """Return cached results when present and not expired."""

    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached is None:
            return None
        created_at, results = cached
        if now - created_at > ttl_seconds:
            _CACHE.pop(key, None)
            return None
        return list(results)


def cache_search_results(
    key: SearchCacheKey, results: list[_SearchResult]
) -> None:
    """Store immutable copies of search results."""

    with _CACHE_LOCK:
        _CACHE[key] = (time.monotonic(), tuple(results))
