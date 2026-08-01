"""Analyzer agent — quantitative confidence scoring for editors."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate

from agents.llm import invoke_llm
from agents.state import AnalysisOutput, ExtractedClaims, StoryAuditState
from agents.utils import strip_json_fences

SYSTEM_PROMPT = """\
You are Analyzer. You score how trustworthy a Dominican news story cluster is
after claim extraction, fact-checking, rhetorical audit, and judgment.

Consume the original story cluster, claims, fact-check, rhetorical audit, and
judgment. Produce structured quantitative output for editors.

Rules:
- overall_confidence MUST be one of: alta, media, baja, en_revision
- confidence_score MUST be a number from 0.0 to 1.0
- source_scores: one entry per distinct outlet in the cluster when possible;
  reliability and corroboration are 0.0–1.0
- metrics.claims_* count claims from the fact-check / claims inputs
- metrics.rhetoric_risk is 0.0–1.0 (higher = more manipulative framing)
- rationale: brief Spanish summary for editors (1–3 sentences)
- Do not rewrite the article. Do not invent sources not present in the inputs.

Output ONLY valid JSON (no markdown fences, no preamble) with this shape:
{{
  "overall_confidence": "alta | media | baja | en_revision",
  "confidence_score": 0.0,
  "source_scores": [
    {{ "source": "Outlet Name", "reliability": 0.0, "corroboration": 0.0 }}
  ],
  "metrics": {{
    "claims_total": 0,
    "claims_supported": 0,
    "claims_contradicted": 0,
    "claims_unverifiable": 0,
    "rhetoric_risk": 0.0
  }},
  "rationale": "Resumen breve en español"
}}
"""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        (
            "human",
            (
                "Original story cluster:\n\n{story}\n\n"
                "Claims:\n\n{claims}\n\n"
                "Fact check results:\n\n{fact_check}\n\n"
                "Rhetorical audit:\n\n{rhetorical_audit}\n\n"
                "Judgment:\n\n{judgment}"
            ),
        ),
    ]
)


def _invalid_analysis(raw: str) -> dict[str, Any]:
    return {
        "confidence": "en_revision",
        "confidence_score": None,
        "source_scores": None,
        "audit_json": {"raw": raw},
    }


def parse_analysis_output(text: str | None) -> AnalysisOutput | None:
    """Return a validated analyzer result, or ``None`` for invalid output."""

    raw = (text or "").strip()
    if not raw:
        return None
    try:
        return AnalysisOutput.model_validate_json(strip_json_fences(raw))
    except (TypeError, ValueError):
        return None


def parse_analysis(text: str | AnalysisOutput | None) -> dict[str, Any]:
    """
    Parse analyzer JSON into persistable fields.

    Returns keys: confidence, confidence_score, source_scores, audit_json.
    On failure: confidence=en_revision, score/source_scores None,
    audit_json={"raw": <original text>}.
    """
    if isinstance(text, AnalysisOutput):
        payload = text
    else:
        raw = (text or "").strip()
        if not raw:
            return _invalid_analysis("")
        payload = parse_analysis_output(raw)
        if payload is None:
            return _invalid_analysis(raw)

    return {
        "confidence": payload.overall_confidence,
        "confidence_score": payload.confidence_score,
        "source_scores": [
            source_score.model_dump() for source_score in payload.source_scores
        ],
        "audit_json": payload.model_dump(),
    }


def run(state: StoryAuditState) -> dict:
    claims_json = ExtractedClaims(
        claims=state.get("claims") or []
    ).model_dump_json(indent=2)
    content = invoke_llm(
        PROMPT,
        {
            "story": state.get("story") or "",
            "claims": claims_json,
            "fact_check": state.get("fact_check") or "",
            "rhetorical_audit": state.get("rhetorical_audit") or "",
            "judgment": state.get("judgment") or "",
        },
    )
    return {
        "analysis": parse_analysis_output(content),
        "messages": [AIMessage(content=content, name="analyzer")],
    }
