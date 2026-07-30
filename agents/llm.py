"""Shared Groq chat model for story-audit agents."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


def get_llm(*, temperature: float = 0) -> ChatGroq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise SystemExit("GROQ_API_KEY is required (set it in .env or the environment)")
    return ChatGroq(model=GROQ_MODEL, temperature=temperature, api_key=api_key)
