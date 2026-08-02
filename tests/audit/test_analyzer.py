"""Analyzer parse helper and story-audit graph wiring."""

from __future__ import annotations

import json

import pytest

from audit.agents.analyzer import parse_analysis, run
from audit.reporting import REPORT_SECTIONS
from audit.state import AnalysisOutput
from audit.story_audit import build_graph, run_audit
from common.db import fetch_verified_article, insert_verified_article


def test_parse_analysis_valid_json():
    raw = json.dumps(
        {
            "overall_confidence": "alta",
            "confidence_score": 0.91,
            "source_scores": [
                {"source": "Listín Diario", "reliability": 0.85, "corroboration": 0.7}
            ],
            "metrics": {
                "claims_total": 12,
                "claims_supported": 8,
                "claims_contradicted": 1,
                "claims_unverifiable": 3,
                "rhetoric_risk": 0.2,
            },
            "rationale": "Alta corroboración entre fuentes.",
        }
    )
    parsed = parse_analysis(raw)
    assert parsed["confidence"] == "alta"
    assert parsed["confidence_score"] == pytest.approx(0.91)
    assert parsed["source_scores"][0]["source"] == "Listín Diario"
    assert parsed["audit_json"]["rationale"].startswith("Alta")


def test_parse_analysis_fenced_json():
    raw = """```json
{"overall_confidence": "media", "confidence_score": 0.55, "source_scores": [],
 "metrics": {"claims_total": 2, "claims_supported": 1, "claims_contradicted": 0,
 "claims_unverifiable": 1, "rhetoric_risk": 0.4},
 "rationale": "Evidencia parcial."}
```"""
    parsed = parse_analysis(raw)
    assert parsed["confidence"] == "media"
    assert parsed["confidence_score"] == pytest.approx(0.55)
    assert parsed["source_scores"] == []


def test_parse_analysis_invalid_defaults_en_revision():
    parsed = parse_analysis("not json at all")
    assert parsed["confidence"] == "en_revision"
    assert parsed["confidence_score"] is None
    assert parsed["source_scores"] is None
    assert parsed["audit_json"] == {"raw": "not json at all"}


def test_parse_analysis_schema_violation_defaults_entire_payload():
    raw = json.dumps(
        {
            "overall_confidence": "super_alta",
            "confidence_score": 1.5,
            "source_scores": "bad",
            "rationale": "x",
        }
    )
    parsed = parse_analysis(raw)
    assert parsed["confidence"] == "en_revision"
    assert parsed["confidence_score"] is None
    assert parsed["source_scores"] is None
    assert parsed["audit_json"] == {"raw": raw}


def test_parse_analysis_rejects_invalid_nested_score():
    raw = json.dumps(
        {
            "overall_confidence": "alta",
            "confidence_score": 0.9,
            "source_scores": [
                {"source": "Hoy", "reliability": 1.2, "corroboration": 0.8}
            ],
            "metrics": {
                "claims_total": 1,
                "claims_supported": 1,
                "claims_contradicted": 0,
                "claims_unverifiable": 0,
                "rhetoric_risk": 0.1,
            },
            "rationale": "Fuente confiable.",
        }
    )
    parsed = parse_analysis(raw)
    assert parsed["confidence"] == "en_revision"
    assert parsed["confidence_score"] is None
    assert parsed["audit_json"] == {"raw": raw}


def test_parse_analysis_accepts_validated_state_model():
    result = AnalysisOutput.model_validate(
        {
            "overall_confidence": "alta",
            "confidence_score": 0.9,
            "source_scores": [],
            "metrics": {
                "claims_total": 1,
                "claims_supported": 1,
                "claims_contradicted": 0,
                "claims_unverifiable": 0,
                "rhetoric_risk": 0.1,
            },
            "rationale": "Resultado validado.",
        }
    )
    parsed = parse_analysis(result)
    assert parsed["confidence"] == "alta"
    assert parsed["confidence_score"] == pytest.approx(0.9)
    assert parsed["audit_json"]["rationale"] == "Resultado validado."


def test_run_adds_validated_analysis_to_state(monkeypatch):
    raw = json.dumps(
        {
            "overall_confidence": "media",
            "confidence_score": 0.6,
            "source_scores": [],
            "metrics": {
                "claims_total": 1,
                "claims_supported": 0,
                "claims_contradicted": 0,
                "claims_unverifiable": 1,
                "rhetoric_risk": 0.2,
            },
            "rationale": "Evidencia incompleta.",
        }
    )
    monkeypatch.setattr("audit.agents.analyzer.invoke_llm", lambda *_args, **_kwargs: raw)
    result = run({"story": "Historia", "claims": []})
    assert isinstance(result["analysis"], AnalysisOutput)
    assert result["analysis"].overall_confidence == "media"
    assert set(result) == {"analysis"}


def test_insert_verified_article_writes_confidence(sqlalchemy_db, monkeypatch):
    monkeypatch.setattr(
        "common.indexing.index_verified_article",
        lambda **_k: None,
    )
    scores = [{"source": "Hoy", "reliability": 0.8, "corroboration": 0.6}]
    audit = {
        "overall_confidence": "baja",
        "confidence_score": 0.3,
        "source_scores": scores,
        "rationale": "Poca corroboración.",
    }
    article_id = insert_verified_article(
        cluster_id="c-analyzer",
        title="Título de prueba",
        content="Cuerpo.",
        status="published",
        confidence="baja",
        confidence_score=0.3,
        source_scores=scores,
        audit_json=audit,
    )
    assert article_id
    row = fetch_verified_article("c-analyzer")
    assert row is not None
    assert row["confidence"] == "baja"
    assert row["confidence_score"] == pytest.approx(0.3)

    source_scores = row["source_scores"]
    if isinstance(source_scores, str):
        source_scores = json.loads(source_scores)
    assert source_scores[0]["source"] == "Hoy"

    audit_json = row["audit_json"]
    if isinstance(audit_json, str):
        audit_json = json.loads(audit_json)
    assert audit_json["overall_confidence"] == "baja"


def test_build_graph_includes_analyzer():
    app = build_graph()
    assert "analyzer" in app.nodes
    assert "judger" in app.nodes
    assert "synthesizer" in app.nodes

    fields = dict(REPORT_SECTIONS)
    assert fields["analyzer"] == "analysis"
    assert list(fields).index("analyzer") == list(fields).index("judger") + 1
    assert list(fields).index("synthesizer") == list(fields).index("analyzer") + 1

    graph = app.get_graph()
    edges = {(e.source, e.target) for e in graph.edges}
    assert ("judger", "analyzer") in edges
    assert ("analyzer", "synthesizer") in edges
    assert ("judger", "synthesizer") not in edges


def test_run_audit_does_not_initialize_messages(capsys):
    seen: list[dict] = []

    class FakeApp:
        def stream(self, state, *, stream_mode):
            seen.append(state)
            assert stream_mode == "updates"
            yield {"synthesizer": {"article": "Titular\n\nCuerpo."}}

    result = run_audit(FakeApp(), "Historia")

    assert seen == [{"story": "Historia"}]
    assert result == {"story": "Historia", "article": "Titular\n\nCuerpo."}
    assert "messages" not in result
    capsys.readouterr()
