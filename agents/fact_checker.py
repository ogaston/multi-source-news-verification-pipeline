"""Fact checker agent — verify claims against external/official sources."""

from __future__ import annotations

import logging
import re
from typing import Literal

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ConfigDict, Field, RootModel, ValidationError

from agents.llm import invoke_llm
from agents.search import (
    SearchBudget,
    SearchProviderError,
    SearchResult,
    search_domains,
)
from agents.state import ExtractedClaim, ExtractedClaims, StoryAuditState
from agents.utils import strip_json_fences
from common.config import (
    FACT_CHECK_MAX_SEARCHES_PER_CLUSTER,
    FACT_CHECK_RESULTS_PER_QUERY,
    FACT_CHECK_TRUSTED_DOMAINS,
)

logger = logging.getLogger(__name__)

INSUFFICIENT_EVIDENCE = "insufficient evidence"
_URL_RE = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)
_VALID_VERDICTS = {"supported", "contradicted", INSUFFICIENT_EVIDENCE}


class FactCheckItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    claim_number: int = Field(ge=1)
    claim_type: Literal["reported", "verifiable_fact"]
    verdict: Literal[
        "supported as reported",
        "supported",
        "contradicted",
        "insufficient evidence",
    ]
    evidence: str
    citations: list[str]


class FactCheckResponse(RootModel[list[FactCheckItem]]):
    pass

SYSTEM_PROMPT = """\
You are Fact Checker for claims extracted from a Dominican news story cluster.

Distinguish two kinds of claims:

1) [reported] claims (what an outlet says someone said or did):
   - If the quote or statement appears in the provided story cluster, label it
     "supported as reported" and cite the outlet (e.g. Nuevo Diario, Facebook).
   - Do NOT mark a quote as contradicted merely because you cannot find it
     elsewhere online. The cluster itself is evidence that it was published.
   - You may note that independent corroboration of the underlying event is lacking.

2) [verifiable_fact] claims at any geographic level (local, Dominican national,
   Caribbean/regional, Latin American, or international):
   - Use only the trusted search evidence supplied for that specific claim.
   - Label: supported, contradicted, or insufficient evidence.
   - Only use "contradicted" when a reliable source clearly disagrees.
   - If no trusted evidence is supplied, use "insufficient evidence".
   - Do not use parametric knowledge or invent contradictions.
   - A supported or contradicted verdict must cite at least one exact URL from
     that claim's trusted evidence. Never create or alter a URL.

Return only a JSON array. Each object must contain:
- claim_number (integer)
- claim_type ("reported" or "verifiable_fact")
- verdict
- evidence (brief notes)
- citations (an array of exact evidence URLs, or an empty array)

Write evidence notes in Spanish. Do not wrap the JSON in Markdown fences.
Do not rewrite the article or analyze rhetoric.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        (
            "human",
            (
                "Story cluster (source of reported claims):\n\n{story}\n\n"
                "Claims to verify:\n\n{claims}\n\n"
                "Trusted search evidence (grouped by claim):\n\n{search_evidence}"
            ),
        ),
    ]
)

def _format_search_evidence(
    claims: list[ExtractedClaim], evidence: dict[int, list[SearchResult]]
) -> str:
    blocks: list[str] = []
    for claim in claims:
        if claim.type != "verifiable_fact":
            continue
        claim_id = claim.id
        results = evidence.get(claim_id, [])
        lines = [f"Claim {claim_id}: {claim.text}"]
        if not results:
            lines.append("NO TRUSTED EVIDENCE FOUND — verdict must be insufficient evidence.")
        else:
            for index, result in enumerate(results, start=1):
                lines.extend(
                    [
                        f"{index}. {result.title}",
                        f"   Domain: {result.domain}",
                        f"   URL: {result.url}",
                        f"   Snippet: {result.snippet}",
                    ]
                )
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) or "No externally verifiable claims."


def _remove_urls(text: str) -> str:
    return _URL_RE.sub("[URL moved to Sources]", str(text or "")).strip()


def _payload_by_claim_number(raw: str) -> dict[int, FactCheckItem]:
    try:
        payload = FactCheckResponse.model_validate_json(strip_json_fences(raw))
    except (TypeError, ValidationError) as exc:
        logger.warning(
            "Fact checker returned invalid JSON; using grounded fallback: %s", exc
        )
        return {}

    indexed: dict[int, FactCheckItem] = {}
    for item in payload.root:
        indexed.setdefault(item.claim_number, item)
    return indexed


def _validate_reported(item: FactCheckItem | None) -> tuple[str, str, list[str]]:
    note = _remove_urls(item.evidence if item else "")
    if not note:
        note = "La afirmación está atribuida en el clúster de noticias."
    return "supported as reported", note, []


def _validate_verifiable(
    item: FactCheckItem | None, results: list[SearchResult]
) -> tuple[str, str, list[str]]:
    note = _remove_urls(item.evidence if item else "")
    allowed_urls = {result.url for result in results}
    supplied = item.citations if item else []
    citations = [value for value in supplied if value in allowed_urls]
    verdict = (item.verdict if item else "").lower()
    if verdict not in _VALID_VERDICTS:
        verdict = INSUFFICIENT_EVIDENCE
    if not allowed_urls:
        return (
            INSUFFICIENT_EVIDENCE,
            "No se encontró evidencia en los dominios autorizados.",
            [],
        )
    if verdict in {"supported", "contradicted"} and not citations:
        return (
            INSUFFICIENT_EVIDENCE,
            "No se proporcionó una cita válida de la evidencia autorizada.",
            [],
        )
    if not note:
        note = "La evidencia autorizada no permite una conclusión más precisa."
    return verdict, note, citations


def _render_claim(
    claim: ExtractedClaim, verdict: str, note: str, citations: list[str]
) -> str:
    lines = [
        f"{claim.id}. [{claim.type}] {claim.text}",
        f"Verdict: {verdict}",
        f"Evidence: {note}",
    ]
    if citations:
        lines.append("Sources: " + ", ".join(dict.fromkeys(citations)))
    return "\n".join(lines)


def validate_fact_check(
    raw: str,
    claims: list[ExtractedClaim],
    evidence: dict[int, list[SearchResult]],
) -> str:
    """Validate LLM verdicts and citations, then render downstream-safe text."""

    by_number = _payload_by_claim_number(raw)
    rendered: list[str] = []
    for claim in claims:
        claim_id = claim.id
        item = by_number.get(claim_id)
        if claim.type == "reported":
            verdict, note, citations = _validate_reported(item)
        else:
            verdict, note, citations = _validate_verifiable(
                item, evidence.get(claim_id, [])
            )
        rendered.append(_render_claim(claim, verdict, note, citations))
    return "\n\n".join(rendered)


def run(state: StoryAuditState) -> dict:
    claims = state.get("claims") or []
    budget = SearchBudget(max_searches=FACT_CHECK_MAX_SEARCHES_PER_CLUSTER)
    evidence: dict[int, list[SearchResult]] = {}
    search_available = True
    for claim in claims:
        if claim.type != "verifiable_fact":
            continue
        claim_id = claim.id
        if not search_available or budget.remaining <= 0:
            evidence[claim_id] = []
            continue
        try:
            evidence[claim_id] = search_domains(
                claim.text,
                FACT_CHECK_TRUSTED_DOMAINS,
                limit=FACT_CHECK_RESULTS_PER_QUERY,
                budget=budget,
            )
        except SearchProviderError as exc:
            logger.warning("Trusted fact-check search unavailable: %s", exc)
            evidence[claim_id] = []
            search_available = False

    claims_json = ExtractedClaims(claims=claims).model_dump_json(indent=2)
    raw = invoke_llm(
        PROMPT,
        {
            "claims": claims_json,
            "story": state.get("story") or "",
            "search_evidence": _format_search_evidence(claims, evidence),
        },
    )
    content = validate_fact_check(raw, claims, evidence)
    return {
        "fact_check": content,
        "messages": [AIMessage(content=content, name="fact_checker")],
    }
