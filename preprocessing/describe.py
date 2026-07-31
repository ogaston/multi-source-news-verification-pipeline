"""Generate Spanish cluster descriptions via DeepSeek."""

from __future__ import annotations

import logging
import re
import time

import httpx

from common.config import (
    CLUSTER_DESC_MAX_CHARS,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
)

logger = logging.getLogger(__name__)

DEEPSEEK_CHAT_URL = f"{DEEPSEEK_BASE_URL}/chat/completions"
# Short Spanish blurb; thinking is off so this need not cover CoT tokens.
DEEPSEEK_DESC_MAX_TOKENS = 1024
DEEPSEEK_MAX_RETRIES = 3
_RETRY_WAIT_RE = re.compile(r"try again in ([\d.]+)\s*s", re.IGNORECASE)


def _system_prompt(max_chars: int) -> str:
    return (
        "Eres un asistente que resume noticias dominicanas. "
        "Dado un conjunto de artículos sobre el mismo tema o evento, "
        f"escribe una breve descripción en español de como máximo {max_chars} caracteres "
        "(idealmente 2-4 oraciones) que sintetice de qué trata la historia. "
        "No inventes hechos; basate solo en los artículos. "
        "No uses viñetas ni títulos. "
        f"No excedas {max_chars} caracteres."
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
    parts.append(f"Descripción breve en español (máximo {max_chars} caracteres):")
    return "\n".join(parts)


def fallback_story_description(
    articles: list[dict],
    *,
    max_chars: int = CLUSTER_DESC_MAX_CHARS,
) -> str:
    """Deterministic summary when DeepSeek is unavailable or returns empty."""
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
        return _truncate(f"{prefix}. {content}", max_chars)
    return _truncate(prefix, max_chars)


def _retry_wait_seconds(response: httpx.Response, attempt: int) -> float:
    match = _RETRY_WAIT_RE.search(response.text or "")
    if match:
        return float(match.group(1)) + 0.5
    return 2.0 * (2 ** (attempt - 1))


def call_deepseek(
    user_prompt: str,
    *,
    api_key: str | None = None,
    model: str = DEEPSEEK_MODEL,
    max_chars: int = CLUSTER_DESC_MAX_CHARS,
    timeout: float = 120.0,
) -> str:
    """Call DeepSeek chat completions and return the assistant message content."""
    key = api_key if api_key is not None else DEEPSEEK_API_KEY
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set")

    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": DEEPSEEK_DESC_MAX_TOKENS,
        "reasoning_effort": "low",
        "thinking": {"type": "disabled"},
        "messages": [
            {"role": "system", "content": _system_prompt(max_chars)},
            {"role": "user", "content": user_prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    last_error: Exception | None = None
    with httpx.Client(timeout=timeout) as client:
        for attempt in range(1, DEEPSEEK_MAX_RETRIES + 1):
            try:
                response = client.post(
                    DEEPSEEK_CHAT_URL, json=payload, headers=headers
                )
                if response.status_code == 429 and attempt < DEEPSEEK_MAX_RETRIES:
                    wait = _retry_wait_seconds(response, attempt)
                    logger.warning(
                        "DeepSeek rate limit; retrying in %.1fs (attempt %s/%s)",
                        wait,
                        attempt,
                        DEEPSEEK_MAX_RETRIES,
                    )
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                data = response.json()
                choices = data.get("choices") or []
                if not choices:
                    return ""
                message = choices[0].get("message") or {}
                content = message.get("content") or ""
                return content.strip()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if (
                    exc.response is not None
                    and exc.response.status_code == 429
                    and attempt < DEEPSEEK_MAX_RETRIES
                ):
                    wait = _retry_wait_seconds(exc.response, attempt)
                    time.sleep(wait)
                    continue
                raise
            except httpx.HTTPError as exc:
                last_error = exc
                raise

    if last_error is not None:
        raise last_error
    return ""


def describe_cluster(
    articles: list[dict],
    *,
    api_key: str | None = None,
    model: str = DEEPSEEK_MODEL,
    max_chars: int = CLUSTER_DESC_MAX_CHARS,
) -> str:
    """
    Generate a Spanish description for a cluster/story.

    Always returns a non-empty string (DeepSeek result or fallback),
    truncated to at most ``max_chars`` characters.
    """
    if not articles:
        return fallback_story_description(articles, max_chars=max_chars)

    prompt = build_cluster_prompt(articles, max_chars=max_chars)
    try:
        description = call_deepseek(
            prompt, api_key=api_key, model=model, max_chars=max_chars
        )
    except Exception as exc:
        logger.warning("DeepSeek cluster description failed: %s", exc)
        return fallback_story_description(articles, max_chars=max_chars)

    description = (description or "").strip()
    if description:
        return _truncate(description, max_chars)
    logger.warning("DeepSeek returned empty content; using fallback description")
    return fallback_story_description(articles, max_chars=max_chars)
