"""Structured-output tests for the claim extractor."""

from __future__ import annotations

import json
from unittest.mock import patch

from agents.claim_extractor import parse_extracted_claims, run
from agents.state import ExtractedClaim


def test_parse_extracted_claims_validates_claim_batch():
    raw = json.dumps(
        {
            "claims": [
                {"id": 8, "type": "reported", "text": "  Se emitió una nota. "},
                {
                    "id": 4,
                    "type": "verifiable_fact",
                    "text": "La tasa fue 20%.",
                },
            ]
        }
    )
    assert [claim.model_dump() for claim in parse_extracted_claims(raw)] == [
        {"id": 8, "type": "reported", "text": "Se emitió una nota."},
        {"id": 4, "type": "verifiable_fact", "text": "La tasa fue 20%."},
    ]


def test_parse_extracted_claims_rejects_invalid_item():
    raw = json.dumps(
        {"claims": [{"id": 1, "type": "opinion", "text": "Es una mala medida."}]}
    )
    assert parse_extracted_claims(raw) == []


def test_parse_extracted_claims_rejects_duplicate_ids():
    raw = json.dumps(
        {
            "claims": [
                {"id": 1, "type": "reported", "text": "Primera."},
                {"id": 1, "type": "verifiable_fact", "text": "Segunda."},
            ]
        }
    )
    assert parse_extracted_claims(raw) == []


def test_parse_extracted_claims_accepts_json_fences():
    raw = """```json
{"claims": [{"id": 1, "type": "verifiable_fact", "text": "Dato."}]}
```"""
    assert parse_extracted_claims(raw) == [
        ExtractedClaim(id=1, type="verifiable_fact", text="Dato.")
    ]


def test_parse_extracted_claims_invalid_json_returns_empty_list():
    assert parse_extracted_claims("not json") == []


def test_run_places_typed_claims_in_graph_state():
    raw = json.dumps(
        {
            "claims": [
                {"id": 1, "type": "reported", "text": "La entidad informó."}
            ]
        }
    )
    with patch("agents.claim_extractor.invoke_llm", return_value=raw):
        result = run({"story": "Historia"})

    assert result["claims"] == [
        ExtractedClaim(id=1, type="reported", text="La entidad informó.")
    ]
    assert json.loads(result["messages"][0].content) == {
        "claims": [claim.model_dump() for claim in result["claims"]]
    }
