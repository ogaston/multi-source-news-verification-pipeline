"""Grounding and routing tests for the fact-checker agent."""

from __future__ import annotations

import json
from typing import Literal
from unittest.mock import patch

from agents.fact_checker import run, validate_fact_check
from agents.search import SearchProviderError, SearchResult
from agents.state import ExtractedClaim


def _result(url: str = "https://one.gob.do/poblacion") -> SearchResult:
    return SearchResult(
        title="Dato oficial",
        url=url,
        snippet="La población registrada es 10.7 millones.",
        domain="gob.do",
    )


def _claim(
    claim_id: int,
    claim_type: Literal["reported", "verifiable_fact"],
    text: str,
) -> ExtractedClaim:
    return ExtractedClaim(id=claim_id, type=claim_type, text=text)


def test_validate_fact_check_accepts_only_exact_returned_citation():
    claims = [_claim(1, "verifiable_fact", "La población es 10.7 millones.")]
    allowed = _result()
    raw = json.dumps(
        [
            {
                "claim_number": 1,
                "claim_type": "verifiable_fact",
                "verdict": "supported",
                "evidence": "La fuente confirma el dato https://evil.example/fake",
                "citations": [allowed.url, "https://evil.example/fake"],
            }
        ]
    )
    output = validate_fact_check(raw, claims, {1: [allowed]})
    assert "Verdict: supported" in output
    assert f"Sources: {allowed.url}" in output
    assert "evil.example" not in output


def test_validate_fact_check_downgrades_ungrounded_verdict():
    claims = [_claim(1, "verifiable_fact", "La tasa fue 20%.")]
    raw = json.dumps(
        [
            {
                "claim_number": 1,
                "claim_type": "verifiable_fact",
                "verdict": "contradicted",
                "evidence": "Conocimiento previo.",
                "citations": [],
            }
        ]
    )
    output = validate_fact_check(raw, claims, {1: [_result()]})
    assert "Verdict: insufficient evidence" in output
    assert "Sources:" not in output


def test_validate_fact_check_invalid_json_uses_safe_fallback():
    claims = [
        _claim(1, "reported", "La entidad emitió un comunicado."),
        _claim(2, "verifiable_fact", "La tasa fue 20%."),
    ]
    output = validate_fact_check("not json", claims, {})
    assert "Verdict: supported as reported" in output
    assert "Verdict: insufficient evidence" in output


def test_run_searches_verifiable_claims_only_and_injects_evidence():
    claims = [
        _claim(1, "reported", "El ministro anunció una medida."),
        _claim(2, "verifiable_fact", "La población es 10.7 millones."),
    ]
    llm_payload = json.dumps(
        [
            {
                "claim_number": 1,
                "claim_type": "reported",
                "verdict": "supported as reported",
                "evidence": "La declaración aparece en el clúster.",
                "citations": [],
            },
            {
                "claim_number": 2,
                "claim_type": "verifiable_fact",
                "verdict": "supported",
                "evidence": "La fuente oficial coincide.",
                "citations": [_result().url],
            },
        ]
    )
    with (
        patch("agents.fact_checker.search_domains", return_value=[_result()]) as search,
        patch("agents.fact_checker.invoke_llm", return_value=llm_payload) as invoke,
    ):
        result = run({"story": "Historia", "claims": claims})

    search.assert_called_once()
    assert search.call_args.args[0] == "La población es 10.7 millones."
    inputs = invoke.call_args.args[1]
    assert json.loads(inputs["claims"]) == {
        "claims": [claim.model_dump() for claim in claims]
    }
    assert _result().url in inputs["search_evidence"]
    assert "Verdict: supported as reported" in result["fact_check"]
    assert "Verdict: supported" in result["fact_check"]


def test_run_search_failure_stops_more_calls_and_forces_insufficient_evidence():
    claims = [
        _claim(1, "verifiable_fact", "Primer dato."),
        _claim(2, "verifiable_fact", "Segundo dato."),
    ]
    attempted = json.dumps(
        [
            {
                "claim_number": 1,
                "claim_type": "verifiable_fact",
                "verdict": "contradicted",
                "evidence": "Sin fuente.",
                "citations": ["https://example.com/fake"],
            },
            {
                "claim_number": 2,
                "claim_type": "verifiable_fact",
                "verdict": "supported",
                "evidence": "Sin fuente.",
                "citations": [],
            },
        ]
    )
    with (
        patch(
            "agents.fact_checker.search_domains",
            side_effect=SearchProviderError("unavailable"),
        ) as search,
        patch("agents.fact_checker.invoke_llm", return_value=attempted),
    ):
        output = run({"story": "Historia", "claims": claims})["fact_check"]

    search.assert_called_once()
    assert output.count("Verdict: insufficient evidence") == 2
    assert "example.com" not in output
