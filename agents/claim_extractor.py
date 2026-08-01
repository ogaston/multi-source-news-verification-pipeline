"""Claim extractor agent — extract checkable claims from clustered news."""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import ValidationError

from agents.llm import invoke_llm
from agents.state import ExtractedClaim, ExtractedClaims, StoryAuditState
from agents.utils import strip_json_fences

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are Claim Extractor for a Dominican news story cluster.

Your job:
- Read the clustered articles about one story.
- Extract discrete, checkable factual claims (who / what / when / where / how much).
- Prefer atomic claims: one assertion per item.
- Quote or paraphrase tightly; preserve names, dates, numbers, and attributions.
- Label each claim as exactly one of:
  - [reported]: the fact that a named person or outlet said, announced, alleged,
    or published something. The cluster itself can support that reporting occurred.
  - [verifiable_fact]: an independently checkable assertion at any geographic
    level—local, Dominican national, Caribbean/regional, Latin American, or
    international.
- When reported speech contains an independently checkable factual assertion,
  split the reporting occurrence and the underlying assertion into separate claims.
- Do not verify claims, judge truth, or rewrite the story.
- Do not invent facts not present in the source material.

Output ONLY valid JSON with this shape:
{{
  "claims": [
    {{"id": 1, "type": "reported", "text": "..."}},
    {{"id": 2, "type": "verifiable_fact", "text": "..."}}
  ]
}}
Do not include Markdown fences, preamble, analysis, or closing remarks.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "Story cluster material:\n\n{story}"),
    ]
)


def parse_extracted_claims(text: str) -> list[ExtractedClaim]:
    """Parse and strictly validate the extractor's JSON response."""

    try:
        payload = ExtractedClaims.model_validate_json(strip_json_fences(text))
    except (TypeError, ValidationError) as exc:
        logger.warning("Claim extractor returned invalid claims JSON: %s", exc)
        return []
    return payload.claims


def run(state: StoryAuditState) -> dict:
    raw = invoke_llm(PROMPT, {"story": state.get("story") or ""})
    claims = parse_extracted_claims(raw)
    content = ExtractedClaims(claims=claims).model_dump_json()
    return {
        "claims": claims,
        "messages": [AIMessage(content=content, name="claim_extractor")],
    }
