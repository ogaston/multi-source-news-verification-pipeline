"""Judger agent — merge evidence and decide what to keep or discard."""

from __future__ import annotations

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate

from agents.llm import get_llm
from agents.state import StoryAuditState

SYSTEM_PROMPT = """\
You are Judger. You receive Fact Checker results and the Rhetorical Auditor report.

Your job:
- Decide what is absolutely false (contradicted by reliable evidence).
- Decide what is not verifiable (insufficient evidence).
- Decide what narrative and claims should be kept for a fair rewrite.
- Weigh rhetorical manipulation: flag misleading framing even when facts are thin.
- Be decisive and explicit; do not rewrite the full article yourself.

Output three buckets: absolutely_false, not_verifiable, narrative_to_keep
(with brief rationale for each item).
"""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        (
            "human",
            "Fact check results:\n\n{fact_check}\n\n"
            "Rhetorical audit:\n\n{rhetorical_audit}",
        ),
    ]
)


def run(state: StoryAuditState) -> dict:
    response = (PROMPT | get_llm()).invoke(
        {
            "fact_check": state.get("fact_check") or "",
            "rhetorical_audit": state.get("rhetorical_audit") or "",
        }
    )
    content = response.content
    return {
        "judgment": content,
        "messages": [AIMessage(content=content, name="judger")],
    }
