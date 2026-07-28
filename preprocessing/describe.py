"""Generate Spanish cluster descriptions via Ollama."""

from __future__ import annotations

import logging

import httpx

from common.config import (
    CLUSTER_DESC_MAX_CHARS,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_THINK,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Eres un asistente que resume noticias dominicanas. "
    "Dado un conjunto de artículos sobre el mismo tema o evento, "
    "escribe una breve descripción en español (2-4 oraciones) que "
    "sintetice de qué trata la historia. No inventes hechos; "
    "basate solo en los artículos. No uses viñetas ni títulos."
)


def _truncate(text: str | None, max_chars: int) -> str:
    value = (text or "").strip()
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 1].rstrip() + "…"


def build_cluster_prompt(
    articles: list[dict],
    *,
    max_chars: int = CLUSTER_DESC_MAX_CHARS,
) -> str:
    """Build the user prompt from cluster member articles."""
    parts: list[str] = [
        "Describe el tema o evento común de estos artículos de noticias:\n"
    ]
    for i, article in enumerate(articles, start=1):
        title = (article.get("title") or "").strip() or "(sin título)"
        source = (article.get("source") or "").strip() or "desconocido"
        date = (article.get("date") or "").strip() or "sin fecha"
        content = _truncate(article.get("content"), max_chars)
        parts.append(
            f"--- Artículo {i} ({source}, {date}) ---\nTítulo: {title}\n{content}\n"
        )
    parts.append("Descripción breve en español:")
    return "\n".join(parts)


def fallback_story_description(
    articles: list[dict],
    *,
    max_chars: int = CLUSTER_DESC_MAX_CHARS,
) -> str:
    """Deterministic summary when Ollama is unavailable or returns empty."""
    if not articles:
        return "Historia sin artículos."

    article = articles[0]
    title = (article.get("title") or "").strip() or "(sin título)"
    source = (article.get("source") or "").strip() or "desconocido"
    date = (article.get("date") or "").strip() or "sin fecha"
    content = _truncate(article.get("content"), max(80, max_chars // 2))
    prefix = f"{title} ({source}, {date})"
    if len(articles) > 1:
        prefix = f"{prefix}; {len(articles)} artículos"
    if content:
        return f"{prefix}. {content}"
    return prefix


def call_ollama(
    user_prompt: str,
    *,
    base_url: str = OLLAMA_BASE_URL,
    model: str = OLLAMA_MODEL,
    timeout: float = 120.0,
) -> str:
    """Call Ollama /api/chat and return the assistant message content."""
    url = f"{base_url.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "stream": False,
        "think": OLLAMA_THINK,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
    content = (data.get("message") or {}).get("content") or ""
    return content.strip()


def describe_cluster(
    articles: list[dict],
    *,
    base_url: str = OLLAMA_BASE_URL,
    model: str = OLLAMA_MODEL,
    max_chars: int = CLUSTER_DESC_MAX_CHARS,
) -> str:
    """
    Generate a Spanish description for a cluster/story.

    Always returns a non-empty string (Ollama result or fallback).
    """
    if not articles:
        return fallback_story_description(articles, max_chars=max_chars)

    prompt = build_cluster_prompt(articles, max_chars=max_chars)
    try:
        description = call_ollama(prompt, base_url=base_url, model=model)
    except Exception as exc:
        logger.warning("Ollama cluster description failed: %s", exc)
        return fallback_story_description(articles, max_chars=max_chars)

    description = (description or "").strip()
    if description:
        return description
    return fallback_story_description(articles, max_chars=max_chars)
