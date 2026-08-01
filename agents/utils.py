"""Shared helpers for story-audit agents."""

from __future__ import annotations

from pydantic import BaseModel


def strip_json_fences(text: str | None) -> str:
    """Remove an optional Markdown code fence from an LLM JSON response."""

    raw = (text or "").strip()
    if not raw.startswith("```"):
        return raw
    lines = raw.splitlines()
    if lines and lines[0].strip().lower() in {"```", "```json"}:
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def pydantic_json_default(value: object) -> object:
    """Serialize Pydantic models for ``json.dumps(default=...)``."""

    if isinstance(value, BaseModel):
        return value.model_dump()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
