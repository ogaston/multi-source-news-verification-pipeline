"""Synthesizer agent — rewrite a neutral, straight article from the judgment."""

from __future__ import annotations

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate

from agents.llm import get_llm
from agents.state import StoryAuditState

SYSTEM_PROMPT = """\
You are Synthesizer. You rewrite the story from Judger's decision.

Your job:
- Write a new article that is unbiased, not misleading, and straight to the point.
- Use only narrative_to_keep; omit absolutely_false material.
- For not_verifiable items, either omit them or clearly mark uncertainty—never present them as fact.
- No sensational headlines, loaded adjectives, or rhetorical devices called out by the auditor.
- Prefer clear attribution and concrete facts over opinion.

Output the rewritten article only (headline + body).
"""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "Judgment:\n\n{judgment}"),
    ]
)


def run(state: StoryAuditState) -> dict:
    response = (PROMPT | get_llm()).invoke(
        {"judgment": state.get("judgment") or ""}
    )
    content = response.content
    return {
        "article": content,
        "messages": [AIMessage(content=content, name="synthesizer")],
    }
