"""Tests for trusted Serper search (all HTTP is mocked)."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from audit.search import (
    SERPER_SEARCH_URL,
    SearchBudget,
    SearchProviderError,
    build_scoped_query,
    search_domains,
    trusted_url_domain,
)
from audit.search_cache import clear_search_cache


@pytest.fixture(autouse=True)
def _empty_search_cache():
    clear_search_cache()
    yield
    clear_search_cache()


def test_build_scoped_query_uses_each_trusted_domain():
    query = build_scoped_query("  población   dominicana ", ["gob.do", "un.org"])
    assert query == "población dominicana (site:gob.do OR site:un.org)"


def test_trusted_url_domain_matches_real_subdomain_not_suffix_attack():
    domains = ("gob.do", "unicef.org")
    assert trusted_url_domain("https://www.one.gob.do/data", domains) == "gob.do"
    assert trusted_url_domain("https://data.unicef.org/topic", domains) == "unicef.org"
    assert trusted_url_domain("https://evilgob.do/data", domains) is None
    assert trusted_url_domain("javascript:alert(1)", domains) is None


def test_search_posts_scoped_payload_and_drops_untrusted_results():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(
            200,
            json={
                "organic": [
                    {
                        "title": "Dato oficial",
                        "link": "https://one.gob.do/dato",
                        "snippet": "Estadística",
                    },
                    {
                        "title": "No permitido",
                        "link": "https://example.com/dato",
                        "snippet": "Ruido",
                    },
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        results = search_domains(
            "dato nacional",
            ("gob.do", "un.org"),
            limit=3,
            api_key="serper-test",
            client=client,
        )

    assert len(results) == 1
    assert results[0].url == "https://one.gob.do/dato"
    request = captured["request"]
    assert str(request.url) == SERPER_SEARCH_URL
    assert request.headers["X-API-KEY"] == "serper-test"
    payload = __import__("json").loads(request.content)
    assert "site:gob.do OR site:un.org" in payload["q"]
    assert payload["gl"] == "do"
    assert payload["hl"] == "es"
    assert payload["num"] == 10


def test_search_retries_transient_status():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, request=request)
        return httpx.Response(200, json={"organic": []}, request=request)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        patch("audit.search.time.sleep") as sleep,
    ):
        assert search_domains("dato", ("gob.do",), api_key="key", client=client) == []

    assert calls == 2
    sleep.assert_called_once()


def test_search_cache_does_not_spend_budget_twice():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"organic": []}, request=request)

    budget = SearchBudget(max_searches=1)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        first = search_domains(
            "dato", ("gob.do",), api_key="key", budget=budget, client=client
        )
        second = search_domains(
            "dato", ("gob.do",), api_key="key", budget=budget, client=client
        )

    assert first == second == []
    assert calls == 1
    assert budget.used == 1


def test_search_budget_exhaustion_skips_http():
    budget = SearchBudget(max_searches=0)
    with patch("audit.search._request_serper") as request:
        assert (
            search_domains("dato", ("gob.do",), api_key="key", budget=budget) == []
        )
    request.assert_not_called()


def test_search_requires_api_key():
    with pytest.raises(SearchProviderError, match="FACT_CHECK_SEARCH_API_KEY"):
        search_domains("dato", ("gob.do",), api_key="")
