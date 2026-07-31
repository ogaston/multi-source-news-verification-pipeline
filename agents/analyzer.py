"""Analyzer agent — quantitative confidence scoring for editors."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate

from agents.llm import invoke_llm
from agents.state import StoryAuditState

CONFIDENCE_LEVELS = frozenset({"alta", "media", "baja", "en_revision"})

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


def _clamp_unit(value: Any) -> float | None:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score


def _strip_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def parse_analysis(text: str | None) -> dict[str, Any]:
    """
    Parse analyzer JSON into persistable fields.

    Returns keys: confidence, confidence_score, source_scores, audit_json.
    On failure: confidence=en_revision, score/source_scores None,
    audit_json={"raw": <original text>}.
    """
    raw = (text or "").strip()
    if not raw:
        return {
            "confidence": "en_revision",
            "confidence_score": None,
            "source_scores": None,
            "audit_json": {"raw": ""},
        }

    try:
        payload = json.loads(_strip_fences(raw))
        if not isinstance(payload, dict):
            raise ValueError("analyzer payload must be a JSON object")
    except ValueError:
        return {
            "confidence": "en_revision",
            "confidence_score": None,
            "source_scores": None,
            "audit_json": {"raw": raw},
        }

    level = payload.get("overall_confidence")
    if not isinstance(level, str) or level not in CONFIDENCE_LEVELS:
        level = "en_revision"

    score = _clamp_unit(payload.get("confidence_score"))

    source_scores = payload.get("source_scores")
    if not isinstance(source_scores, list):
        source_scores = None

    return {
        "confidence": level,
        "confidence_score": score,
        "source_scores": source_scores,
        "audit_json": payload,
    }


def run(state: StoryAuditState) -> dict:
    content = invoke_llm(
        PROMPT,
        {
            "story": state.get("story") or "",
            "claims": state.get("claims") or "",
            "fact_check": state.get("fact_check") or "",
            "rhetorical_audit": state.get("rhetorical_audit") or "",
            "judgment": state.get("judgment") or "",
        },
    )
    return {
        "analysis": content,
        "messages": [AIMessage(content=content, name="analyzer")],
    }
