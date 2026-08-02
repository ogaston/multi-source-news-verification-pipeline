"""Domain-restricted Serper search for grounded fact checking."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from audit.search_cache import (
    SearchCacheKey,
    cache_search_results,
    get_cached_search_results,
)
from common.config import (
    FACT_CHECK_RESULTS_PER_QUERY,
    FACT_CHECK_SEARCH_API_KEY,
    FACT_CHECK_SEARCH_CACHE_TTL_SECONDS,
    FACT_CHECK_SEARCH_GEO,
    FACT_CHECK_SEARCH_LANG,
    FACT_CHECK_SEARCH_TIMEOUT_SECONDS,
    FACT_CHECK_TRUSTED_DOMAINS,
)

SERPER_SEARCH_URL = "https://google.serper.dev/search"
MAX_RETRIES = 3
_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchResult:
    """A trusted organic result returned by Serper."""

    title: str
    url: str
    snippet: str
    domain: str


class SearchProviderError(RuntimeError):
    """Raised when trusted search cannot be completed."""


@dataclass
class SearchBudget:
    """Per-story-cluster cap on external API requests."""

    max_searches: int
    used: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.max_searches - self.used)

    def acquire(self) -> bool:
        if self.remaining <= 0:
            return False
        self.used += 1
        return True


def normalize_domain(domain: str) -> str:
    """Normalize a configured hostname or URL to an allowlist hostname."""

    value = (domain or "").strip().lower().rstrip(".")
    if "://" in value:
        value = urlparse(value).hostname or ""
    if value.startswith("www."):
        value = value[4:]
    return value


def trusted_url_domain(
    url: str, domains: tuple[str, ...] | list[str] = FACT_CHECK_TRUSTED_DOMAINS
) -> str | None:
    """Return the matching trusted domain for an HTTP(S) URL."""

    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    hostname = parsed.hostname.lower().rstrip(".")
    for raw_domain in domains:
        domain = normalize_domain(raw_domain)
        if domain and (hostname == domain or hostname.endswith(f".{domain}")):
            return domain
    return None


def build_scoped_query(query: str, domains: tuple[str, ...] | list[str]) -> str:
    """Build a Google query constrained with explicit ``site:`` operators."""

    clean_query = " ".join((query or "").split())
    clean_domains = tuple(
        dict.fromkeys(
            domain
            for domain in (normalize_domain(item) for item in domains)
            if domain
        )
    )
    if not clean_query:
        raise ValueError("search query must not be empty")
    if not clean_domains:
        raise ValueError("at least one trusted domain is required")
    sites = " OR ".join(f"site:{domain}" for domain in clean_domains)
    return f"{clean_query} ({sites})"


def _request_serper(
    scoped_query: str,
    *,
    api_key: str,
    candidate_count: int,
    geo: str,
    lang: str,
    timeout: float,
    client: httpx.Client | None,
) -> dict:
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {
        "q": scoped_query,
        "num": candidate_count,
        "gl": geo,
        "hl": lang,
    }
    owns_client = client is None
    active_client = client or httpx.Client(timeout=timeout)
    try:
        return _request_with_retries(active_client, headers, payload)
    finally:
        if owns_client:
            active_client.close()


def _request_with_retries(
    client: httpx.Client, headers: dict[str, str], payload: dict
) -> dict:
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.post(SERPER_SEARCH_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise SearchProviderError("Serper returned a non-object response")
            return data
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code not in _RETRYABLE_STATUS_CODES:
                raise SearchProviderError(
                    f"Serper request failed with HTTP {exc.response.status_code}"
                ) from exc
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_error = exc
        except ValueError as exc:
            raise SearchProviderError("Serper returned invalid JSON") from exc
        if attempt < MAX_RETRIES:
            time.sleep(0.5 * (2 ** (attempt - 1)))
    raise SearchProviderError("Serper request failed after retries") from last_error


def _trusted_results(
    organic: object,
    domains: tuple[str, ...],
    limit: int,
) -> tuple[list[SearchResult], int]:
    if not isinstance(organic, list):
        return [], 0
    accepted: list[SearchResult] = []
    rejected = 0
    for item in organic:
        if not isinstance(item, dict):
            rejected += 1
            continue
        url = str(item.get("link") or "").strip()
        domain = trusted_url_domain(url, domains)
        if not domain:
            rejected += 1
            continue
        accepted.append(
            SearchResult(
                title=str(item.get("title") or "").strip(),
                url=url,
                snippet=str(item.get("snippet") or "").strip(),
                domain=domain,
            )
        )
        if len(accepted) >= limit:
            break
    return accepted, rejected


def search_domains(
    query: str,
    domains: tuple[str, ...] | list[str] = FACT_CHECK_TRUSTED_DOMAINS,
    *,
    limit: int = FACT_CHECK_RESULTS_PER_QUERY,
    api_key: str = FACT_CHECK_SEARCH_API_KEY,
    budget: SearchBudget | None = None,
    geo: str = FACT_CHECK_SEARCH_GEO,
    lang: str = FACT_CHECK_SEARCH_LANG,
    timeout: float = FACT_CHECK_SEARCH_TIMEOUT_SECONDS,
    cache_ttl_seconds: int = FACT_CHECK_SEARCH_CACHE_TTL_SECONDS,
    client: httpx.Client | None = None,
) -> list[SearchResult]:
    """Search Serper and return only results that pass the domain allowlist."""

    clean_domains = tuple(
        dict.fromkeys(
            domain
            for domain in (normalize_domain(item) for item in domains)
            if domain
        )
    )
    requested_limit = max(0, limit)
    if requested_limit == 0:
        return []
    scoped_query = build_scoped_query(query, clean_domains)
    key: SearchCacheKey = (
        scoped_query,
        clean_domains,
        requested_limit,
        geo,
        lang,
    )
    cached = get_cached_search_results(key, cache_ttl_seconds)
    if cached is not None:
        return cached
    if budget is not None and not budget.acquire():
        logger.info("Serper search skipped: per-cluster budget exhausted")
        return []
    if not api_key:
        raise SearchProviderError(
            "FACT_CHECK_SEARCH_API_KEY (or SERPER_API_KEY) is required"
        )

    started_at = time.monotonic()
    data = _request_serper(
        scoped_query,
        api_key=api_key,
        candidate_count=min(100, max(10, requested_limit * 3)),
        geo=geo,
        lang=lang,
        timeout=timeout,
        client=client,
    )
    accepted, rejected = _trusted_results(
        data.get("organic"), clean_domains, requested_limit
    )

    elapsed_ms = round((time.monotonic() - started_at) * 1000)
    logger.info(
        "Serper trusted search query=%r domains=%s accepted=%d rejected=%d "
        "latency_ms=%d",
        query,
        ",".join(clean_domains),
        len(accepted),
        rejected,
        elapsed_ms,
    )
    cache_search_results(key, accepted)
    return accepted
