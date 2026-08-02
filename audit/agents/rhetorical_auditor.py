"""Rhetorical auditor agent — intent, fallacies, and framing analysis."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from audit.llm import invoke_llm
from audit.state import StoryAuditState

SYSTEM_PROMPT = """\
You are Rhetorical Auditor for a Dominican news story cluster.

Your job:
- Analyze intention, framing, loaded language, omissions, and logical fallacies.
- Call out sensationalism, false balance, guilt by association, and similar devices.
- Describe how the narrative steers the reader; stay descriptive, not moralizing.
- Do not fact-check claims or decide what is true or false.

Output a short structured audit: intent, devices/fallacies found, framing notes.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "Story cluster material:\n\n{story}"),
    ]
)


def run(state: StoryAuditState) -> dict:
    content = invoke_llm(PROMPT, {"story": state.get("story") or ""})
    return {"rhetorical_audit": content}
