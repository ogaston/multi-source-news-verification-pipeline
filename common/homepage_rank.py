"""Homepage ranking helpers: lead tiebreak and 1+8+8 slot split."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Sequence
from typing import Any, TypeVar

from common.config import (
    DEEPINFRA_API_KEY,
    DEEPINFRA_BASE_URL,
    DEEPINFRA_MODEL,
    HOMEPAGE_LIST_COUNT,
    HOMEPAGE_SECONDARY_COUNT,
)
from common.deepinfra_chat import DEFAULT_MAX_RETRIES, chat_completion

logger = logging.getLogger(__name__)

T = TypeVar("T")

_SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")

_TIEBREAK_SYSTEM = (
    "Eres el editor jefe de un diario dominicano. "
    "Elige la noticia más importante para la portada. "
    "Responde SOLO con el slug exacto de la noticia elegida."
)


def cluster_size_of(row: dict[str, Any]) -> int:
    value = row.get("cluster_size")
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def apply_lead_tiebreak(
    rows: Sequence[dict[str, Any]],
    *,
    pick_lead: Callable[[Sequence[dict[str, Any]]], str] | None = None,
) -> list[dict[str, Any]]:
    """
    Move the LLM-chosen lead to index 0 when multiple top rows share
    the same max cluster_size. Otherwise return rows unchanged.
    """
    ordered = list(rows)
    if len(ordered) < 2:
        return ordered

    top_size = cluster_size_of(ordered[0])
    if top_size <= 0:
        return ordered

    tied = [row for row in ordered if cluster_size_of(row) == top_size]
    if len(tied) < 2:
        return ordered

    picker = pick_lead or llm_pick_lead_slug
    try:
        chosen_slug = (picker(tied) or "").strip()
    except Exception:
        logger.exception("homepage lead tiebreak failed; keeping SQL order")
        return ordered

    tied_slugs = {row.get("slug") for row in tied}
    if not chosen_slug or chosen_slug not in tied_slugs:
        return ordered

    chosen_idx = next(
        (i for i, row in enumerate(ordered) if row.get("slug") == chosen_slug),
        None,
    )
    if chosen_idx is None or chosen_idx == 0:
        return ordered

    chosen = ordered.pop(chosen_idx)
    return [chosen, *ordered]


def llm_pick_lead_slug(candidates: Sequence[dict[str, Any]]) -> str:
    """Ask DeepInfra which tied candidate should lead the homepage."""
    if not candidates:
        return ""
    if len(candidates) == 1:
        return str(candidates[0].get("slug") or "")

    key = DEEPINFRA_API_KEY
    if not key:
        return str(candidates[0].get("slug") or "")

    lines = []
    for row in candidates:
        slug = row.get("slug") or ""
        title = (row.get("title") or "").strip()
        summary = (row.get("content") or "").strip().split("\n\n", 1)[0][:280]
        lines.append(f"- slug: {slug}\n  título: {title}\n  resumen: {summary}")

    user_prompt = (
        "Estas noticias empataron en importancia (mismo tamaño de cluster). "
        "Elige la más relevante para la portada de hoy:\n\n"
        + "\n".join(lines)
        + "\n\nResponde solo con el slug."
    )

    content = chat_completion(
        [
            {"role": "system", "content": _TIEBREAK_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        api_key=key,
        model=DEEPINFRA_MODEL,
        timeout=30.0,
        max_retries=DEFAULT_MAX_RETRIES,
        base_url=DEEPINFRA_BASE_URL,
        temperature=0,
        max_tokens=64,
        chat_template_kwargs={"enable_thinking": False},
    )
    text = str(content or "").strip()
    match = _SLUG_RE.search(text.casefold().replace("_", "-"))
    if not match:
        return str(candidates[0].get("slug") or "")

    matched = match.group(0)
    for row in candidates:
        slug = str(row.get("slug") or "")
        if slug == matched or slug.casefold() == matched:
            return slug
    return str(candidates[0].get("slug") or "")


def split_home_articles(
    articles: Sequence[T],
    *,
    secondary_count: int = HOMEPAGE_SECONDARY_COUNT,
    list_count: int = HOMEPAGE_LIST_COUNT,
) -> tuple[T | None, list[T], list[T]]:
    """Split a relevance-ordered list into lead, secondary (left), list (right)."""
    items = list(articles)
    if not items:
        return None, [], []
    lead = items[0]
    rest = items[1:]
    secondary = rest[:secondary_count]
    listing = rest[secondary_count : secondary_count + list_count]
    return lead, secondary, listing
