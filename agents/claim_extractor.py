"""Claim extractor agent — extract checkable claims from clustered news."""

from __future__ import annotations

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate

from agents.llm import invoke_llm
from agents.state import StoryAuditState

SYSTEM_PROMPT = """\
You are Claim Extractor for a Dominican news story cluster.

Your job:
- Read the clustered articles about one story.
- Extract discrete, checkable factual claims (who / what / when / where / how much).
- Prefer atomic claims: one assertion per item.
- Quote or paraphrase tightly; preserve names, dates, numbers, and attributions.
- Do not verify claims, judge truth, or rewrite the story.
- Do not invent facts not present in the source material.

Output a clear numbered list of claims only.
Do not include preamble, analysis, or closing remarks—only the numbered claims.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "Story cluster material:\n\n{story}"),
    ]
)


def run(state: StoryAuditState) -> dict:
    content = invoke_llm(PROMPT, {"story": state.get("story") or ""})
    return {
        "claims": content,
        "messages": [AIMessage(content=content, name="claim_extractor")],
    }
