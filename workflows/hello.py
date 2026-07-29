"""Hello-world LangGraph workflow with two Groq-powered agents.

Usage:
  python -m workflows.hello
  python -m workflows.hello "Dominican news"
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, START, MessagesState, StateGraph

load_dotenv()

GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


def _llm() -> ChatGroq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise SystemExit("GROQ_API_KEY is required (set it in .env or the environment)")
    return ChatGroq(model=GROQ_MODEL, temperature=0, api_key=api_key)


def greeter(state: MessagesState) -> dict:
    """Agent 1: write a short greeting about the topic."""
    llm = _llm()
    response = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are Greeter. Write one short, friendly hello message "
                    "about the user's topic. Keep it to 1-2 sentences."
                )
            ),
            *state["messages"],
        ]
    )
    return {"messages": [AIMessage(content=response.content, name="greeter")]}


def responder(state: MessagesState) -> dict:
    """Agent 2: reply to the greeter's message."""
    llm = _llm()
    response = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are Responder. Reply warmly to the greeter's message. "
                    "Keep it to 1-2 sentences."
                )
            ),
            *state["messages"],
        ]
    )
    return {"messages": [AIMessage(content=response.content, name="responder")]}


def build_graph():
    graph = StateGraph(MessagesState)
    graph.add_node("greeter", greeter)
    graph.add_node("responder", responder)
    graph.add_edge(START, "greeter")
    graph.add_edge("greeter", "responder")
    graph.add_edge("responder", END)
    return graph.compile()


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    topic = args[0] if args else "world"

    app = build_graph()
    result = app.invoke({"messages": [HumanMessage(content=f"Say hello about: {topic}")]})

    for msg in result["messages"]:
        role = getattr(msg, "name", None) or msg.type
        print(f"[{role}] {msg.content}")


if __name__ == "__main__":
    main()
