"""Fact checker agent — verify claims against external/official sources."""

from __future__ import annotations

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate

from agents.llm import invoke_llm
from agents.state import StoryAuditState

SYSTEM_PROMPT = """\
You are Fact Checker for claims extracted from a Dominican news story cluster.

Distinguish two kinds of claims:

1) Reported speech / coverage claims (what an outlet says someone said or did):
   - If the quote or statement appears in the provided story cluster, label it
     "supported as reported" and cite the outlet (e.g. Nuevo Diario, Facebook).
   - Do NOT mark a quote as contradicted merely because you cannot find it
     elsewhere online. The cluster itself is evidence that it was published.
   - You may note that independent corroboration of the underlying event is lacking.

2) World facts (medals, dates, birthplace, medal tables, identities):
   - Check against external/official sources when available.
   - Label: supported, contradicted, or insufficient evidence.
   - Only use "contradicted" when a reliable source clearly disagrees.
   - Do not invent contradictions. If your knowledge cutoff or search cannot
     confirm recent events, use "insufficient evidence", not "contradicted".

For every claim: verdict + brief evidence notes.
Do not rewrite the article or analyze rhetoric.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        (
            "human",
            "Story cluster (source of reported claims):\n\n{story}\n\n"
            "Claims to verify:\n\n{claims}",
        ),
    ]
)


def run(state: StoryAuditState) -> dict:
    content = invoke_llm(
        PROMPT,
        {
            "claims": state.get("claims") or "",
            "story": state.get("story") or "",
        },
    )
    return {
        "fact_check": content,
        "messages": [AIMessage(content=content, name="fact_checker")],
    }
