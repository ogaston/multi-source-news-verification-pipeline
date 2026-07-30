"""LangGraph story-audit workflow (Groq-backed agents).

Agents live in sibling modules (each with SYSTEM_PROMPT + ChatPromptTemplate + run).

Usage:
  python -m agents.story_audit
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agents.claim_extractor import run as claim_extractor
from agents.fact_checker import run as fact_checker
from agents.judger import run as judger
from agents.rhetorical_auditor import run as rhetorical_auditor
from agents.state import StoryAuditState
from agents.synthesizer import run as synthesizer


def build_graph():
    graph = StateGraph(StoryAuditState)
    graph.add_node("claim_extractor", claim_extractor)
    graph.add_node("fact_checker", fact_checker)
    graph.add_node("rhetorical_auditor", rhetorical_auditor)
    # defer so judger waits for both branches (fact_checker + rhetorical_auditor)
    graph.add_node("judger", judger, defer=True)
    graph.add_node("synthesizer", synthesizer)

    graph.add_edge(START, "claim_extractor")
    graph.add_edge(START, "rhetorical_auditor")
    graph.add_edge("claim_extractor", "fact_checker")
    graph.add_edge("fact_checker", "judger")
    graph.add_edge("rhetorical_auditor", "judger")
    graph.add_edge("judger", "synthesizer")
    graph.add_edge("synthesizer", END)
    return graph.compile()


STORY = """
"""


def main() -> None:
    app = build_graph()
    # Story sourcing is deferred; empty story until wired to DB/MCP.
    result = app.invoke({"messages": [], "story": ""})

    for msg in result["messages"]:
        role = getattr(msg, "name", None) or msg.type
        print(f"[{role}] {msg.content}")


if __name__ == "__main__":
    main()
