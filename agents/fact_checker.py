"""Fact checker agent — verify claims against external/official sources."""

from __future__ import annotations

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate

from agents.llm import get_llm
from agents.state import StoryAuditState

SYSTEM_PROMPT = """\
You are Fact Checker for claims extracted from Dominican news.

Your job:
- Take each claim from Claim Extractor.
- Check it against external and official sources (government sites, regulators,
  primary documents, reputable wire/data sources) when available.
- For every claim, label: supported, contradicted, or insufficient evidence.
- Cite the source(s) you relied on; note when you could not find a reliable check.
- Do not rewrite the article or analyze rhetoric; stay on veracity only.

Output a structured list: claim → verdict → brief evidence notes.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        (
            "human",
            "Claims to verify:\n\n{claims}\n\nStory context (optional):\n\n{story}",
        ),
    ]
)


def run(state: StoryAuditState) -> dict:
    response = (PROMPT | get_llm()).invoke(
        {
            "claims": state.get("claims") or "",
            "story": state.get("story") or "",
        }
    )
    content = response.content
    return {
        "fact_check": content,
        "messages": [AIMessage(content=content, name="fact_checker")],
    }
