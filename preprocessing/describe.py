"""Generate Spanish cluster descriptions via DeepInfra."""

from __future__ import annotations

import json
import logging
import re
from typing import TypedDict

from common.config import (
    CLUSTER_DESC_MAX_CHARS,
    DEEPINFRA_API_KEY,
    DEEPINFRA_BASE_URL,
    DEEPINFRA_MODEL,
)
from common.deepinfra_chat import chat_completion
from common.taxonomy import (
    ALLOWED_CATEGORIES,
    DEFAULT_CATEGORY,
    DEFAULT_PLACE,
    normalize_category,
    normalize_place,
)

logger = logging.getLogger(__name__)

CLUSTER_LLM_CHAT_URL = f"{DEEPINFRA_BASE_URL}/chat/completions"
CLUSTER_DESC_MAX_TOKENS = 1024
CLUSTER_LLM_MAX_RETRIES = 3
_JSON_FENCE_RE = re.compile(
    r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE
)


class ClusterMetadata(TypedDict):
    description: str
    category: str
    place: str


def _system_prompt(max_chars: int) -> str:
    categories = ", ".join(ALLOWED_CATEGORIES)
    return (
        "Eres un asistente que resume noticias dominicanas. "
        "Dado un conjunto de artículos sobre el mismo tema o evento, "
        "responde ÚNICAMENTE con un objeto JSON válido (sin markdown) con "
        "estas claves:\n"
        f'- "description": breve descripción en español de como máximo {max_chars} '
        "caracteres (idealmente 2-4 oraciones) que sintetice de qué trata la "
        "historia. No inventes hechos; basate solo en los artículos. "
        "No uses viñetas ni títulos. No inicies con una ubicación o dateline.\n"
        f'- "category": exactamente una de: {categories}.\n'
        '- "place": ciudad, provincia o ámbito donde ocurrió el hecho '
        '(español dominicano). Si no está claro, usa "Nacional" o "Internacional".\n'
        f"No excedas {max_chars} caracteres en description."
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
        "Describe el tema o evento común de estos artículos de noticias "
        "y asigna categoría y lugar. Responde solo con JSON:\n"
    ]
    for i, article in enumerate(articles, start=1):
        title = (article.get("title") or "").strip() or "(sin título)"
        source = (article.get("source") or "").strip() or "desconocido"
        date = (article.get("date") or "").strip() or "sin fecha"
        content = _truncate(article.get("content"), max_chars)
        parts.append(
            f"--- Artículo {i} ({source}, {date}) ---\nTítulo: {title}\n{content}\n"
        )
    parts.append(
        f'Respuesta JSON con "description" (máximo {max_chars} caracteres), '
        '"category" y "place":'
    )
    return "\n".join(parts)


def fallback_story_description(
    articles: list[dict],
    *,
    max_chars: int = CLUSTER_DESC_MAX_CHARS,
) -> str:
    """Deterministic summary when the cluster LLM is unavailable or returns empty."""
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


def fallback_cluster_metadata(
    articles: list[dict],
    *,
    max_chars: int = CLUSTER_DESC_MAX_CHARS,
) -> ClusterMetadata:
    category = DEFAULT_CATEGORY
    for article in articles:
        normalized = normalize_category(article.get("category"))
        if (article.get("category") or "").strip():
            category = normalized
            break
    return {
        "description": fallback_story_description(articles, max_chars=max_chars),
        "category": category,
        "place": normalize_place(DEFAULT_PLACE),
    }


def parse_cluster_metadata(
    raw: str | None,
    *,
    max_chars: int = CLUSTER_DESC_MAX_CHARS,
) -> ClusterMetadata | None:
    """Parse cluster-LLM JSON (or fenced JSON) into cluster metadata."""
    text = (raw or "").strip()
    if not text:
        return None

    candidates = [text]
    fence = _JSON_FENCE_RE.search(text)
    if fence:
        candidates.insert(0, fence.group(1).strip())
    # Sometimes the model adds prose around a JSON object.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(text[start : end + 1])

    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        description = _truncate(str(data.get("description") or ""), max_chars)
        if not description:
            continue
        return {
            "description": description,
            "category": normalize_category(
                str(data.get("category") or "")
                if data.get("category") is not None
                else ""
            ),
            "place": normalize_place(
                str(data.get("place") or "") if data.get("place") is not None else ""
            ),
        }
    return None


def call_cluster_llm(
    user_prompt: str,
    *,
    api_key: str | None = None,
    model: str = DEEPINFRA_MODEL,
    max_chars: int = CLUSTER_DESC_MAX_CHARS,
    timeout: float = 120.0,
) -> str:
    """Call DeepInfra chat completions and return the assistant message content."""
    key = api_key if api_key is not None else DEEPINFRA_API_KEY
    if not key:
        raise RuntimeError("DEEPINFRA_API_KEY is not set")

    print(f"[cluster-llm] calling {model}...", flush=True)
    text = chat_completion(
        [
            {"role": "system", "content": _system_prompt(max_chars)},
            {"role": "user", "content": user_prompt},
        ],
        api_key=key,
        model=model,
        timeout=timeout,
        max_retries=CLUSTER_LLM_MAX_RETRIES,
        base_url=DEEPINFRA_BASE_URL,
        temperature=0,
        max_tokens=CLUSTER_DESC_MAX_TOKENS,
        # Qwen3.x defaults to thinking mode; keep responses short JSON only.
        chat_template_kwargs={"enable_thinking": False},
    )
    if not text:
        print("[cluster-llm] empty choices in response", flush=True)
        return ""
    print(f"[cluster-llm] got {len(text)} chars", flush=True)
    return text


def describe_cluster(
    articles: list[dict],
    *,
    api_key: str | None = None,
    model: str = DEEPINFRA_MODEL,
    max_chars: int = CLUSTER_DESC_MAX_CHARS,
) -> ClusterMetadata:
    """
    Generate Spanish description, category, and place for a cluster/story.

    Always returns non-empty metadata (DeepInfra result or fallback).
    """
    if not articles:
        print("[describe] empty cluster; using fallback", flush=True)
        return fallback_cluster_metadata(articles, max_chars=max_chars)

    title = (articles[0].get("title") or "").strip() or "(sin título)"
    print(
        f"[describe] {len(articles)} articles, lead={title[:100]!r}...",
        flush=True,
    )
    prompt = build_cluster_prompt(articles, max_chars=max_chars)
    try:
        raw = call_cluster_llm(
            prompt, api_key=api_key, model=model, max_chars=max_chars
        )
    except Exception as exc:
        print(f"[describe] LLM failed: {exc}; using fallback", flush=True)
        logger.warning("DeepInfra cluster description failed: %s", exc)
        return fallback_cluster_metadata(articles, max_chars=max_chars)

    parsed = parse_cluster_metadata(raw, max_chars=max_chars)
    if parsed:
        print(
            f"[describe] parsed JSON -> {parsed['category']} / {parsed['place']}",
            flush=True,
        )
        return parsed

    # Plain-text response: keep description, use defaults for category/place.
    description = _truncate((raw or "").strip(), max_chars)
    if description:
        print(
            f"[describe] non-JSON reply; keeping plain text "
            f"(defaults for category/place): {description[:120]!r}",
            flush=True,
        )
        logger.warning(
            "DeepInfra returned non-JSON description; using defaults for category/place"
        )
        return {
            "description": description,
            "category": DEFAULT_CATEGORY,
            "place": normalize_place(DEFAULT_PLACE),
        }

    print("[describe] empty LLM content; using fallback", flush=True)
    logger.warning("DeepInfra returned empty content; using fallback description")
    return fallback_cluster_metadata(articles, max_chars=max_chars)
