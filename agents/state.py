"""Shared LangGraph state for the story-audit workflow."""

from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class StoryAuditState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    story: str
    claims: str
    fact_check: str
    rhetorical_audit: str
    judgment: str
    article: str
