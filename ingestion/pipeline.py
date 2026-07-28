"""Date normalization and quality gates before persistence."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from common.config import MIN_CONTENT_CHARS

_PLACEHOLDER_TITLES = {"", "sin título", "sin titulo"}
_PLACEHOLDER_CONTENT = {"", "sin contenido"}
_PLACEHOLDER_DATES = {"", "sin fecha"}

_JUNK_URL_PATTERNS = (
    r"pregunta-del-dia",
    r"horoscopo",
    r"horóscopo",
    r"/encuesta",
    r"/encuestas/",
    r"/loterias?/",
    r"/obituarios?/",
    r"/galerias?/",
    r"/podcasts?/",
    r"/videos?/",
)

_JUNK_TITLE_PATTERNS = (
    r"pregunta del d[ií]a",
    r"hor[oó]scopo",
    r"^encuesta\b",
)


def normalize_date(raw: str | None) -> str | None:
    """Parse a date string and return UTC ISO-8601, or None if unusable."""
    if raw is None:
        return None

    text = str(raw).strip()
    if not text or text.lower() in _PLACEHOLDER_DATES:
        return None

    # Normalize trailing Z for fromisoformat
    candidate = text.replace("Z", "+00:00") if text.endswith("Z") else text

    parsed: datetime | None = None
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        pass

    if parsed is None:
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y",
        ):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue

    if parsed is None:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)

    return parsed.isoformat().replace("+00:00", "Z")


def validate_article(article: dict) -> str | None:
    """
    Return a skip reason if the article should not be saved, else None.
    Expects `date` already normalized (UTC ISO) when present.
    """
    title = (article.get("title") or "").strip()
    content = (article.get("content") or "").strip()
    url = (article.get("url") or "").strip()
    date = article.get("date")

    if title.lower() in _PLACEHOLDER_TITLES:
        return "missing or placeholder title"

    if content.lower() in _PLACEHOLDER_CONTENT:
        return "missing or placeholder content"

    if len(content) < MIN_CONTENT_CHARS:
        return f"content too short ({len(content)} < {MIN_CONTENT_CHARS})"

    if not date or not normalize_date(str(date)):
        return "missing or unparseable date"

    url_lower = url.lower()
    for pattern in _JUNK_URL_PATTERNS:
        if re.search(pattern, url_lower):
            return f"junk URL pattern: {pattern}"

    title_lower = title.lower()
    for pattern in _JUNK_TITLE_PATTERNS:
        if re.search(pattern, title_lower):
            return f"junk title pattern: {pattern}"

    return None


def prepare_article(article: dict) -> tuple[dict | None, str | None]:
    """
    Normalize date and validate. Returns (article, None) on success,
    or (None, reason) on skip.
    """
    normalized = normalize_date(article.get("date"))
    prepared = {**article, "date": normalized}
    reason = validate_article(prepared)
    if reason:
        return None, reason
    return prepared, None
