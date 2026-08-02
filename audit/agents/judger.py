"""Judger agent — merge evidence and decide what to keep or discard."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from audit.llm import invoke_llm
from audit.state import StoryAuditState

SYSTEM_PROMPT = """\
You are Judger. You receive Fact Checker results, the Rhetorical Auditor report,
and the original story cluster topic.

Your job:
- Decide what is absolutely_false (clearly contradicted by reliable evidence).
- Decide what is not_verifiable (insufficient independent evidence).
- Decide what belongs in narrative_to_keep for a fair rewrite.

Critical rules:
- Preserve the CORE TOPIC of the cluster in narrative_to_keep. If the sources
  are about racist attacks / nationality / identity statements, that topic must
  remain in narrative_to_keep—do not reduce the story to an unrelated bio blurb.
- Claims marked "supported as reported" (quotes or statements published in the
  cluster outlets) go in narrative_to_keep WITH attribution
  (e.g. "Según El Nuevo Diario, Pie dijo…"). They are not absolutely_false.
- Put underlying events that lack independent corroboration in not_verifiable
  if needed, but still keep the attributed reporting in narrative_to_keep.
- Only use absolutely_false for claims a reliable source clearly contradicts.
- Weigh rhetorical manipulation: keep the facts/reported speech, drop loaded framing.
- Be decisive and explicit; do not rewrite the full article yourself.

Output three buckets: absolutely_false, not_verifiable, narrative_to_keep
(with brief rationale for each item).
"""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        (
            "human",
            (
                "Original story cluster (for topic fidelity):\n\n{story}\n\n"
                "Fact check results:\n\n{fact_check}\n\n"
                "Rhetorical audit:\n\n{rhetorical_audit}"
            ),
        ),
    ]
)


def run(state: StoryAuditState) -> dict:
    content = invoke_llm(
        PROMPT,
        {
            "story": state.get("story") or "",
            "fact_check": state.get("fact_check") or "",
            "rhetorical_audit": state.get("rhetorical_audit") or "",
        },
    )
    return {"judgment": content}
