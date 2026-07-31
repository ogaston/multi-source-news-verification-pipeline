"""Map DB verified_articles rows to public Article responses."""

from __future__ import annotations

import re
from typing import Any

from api.schemas import Article, ArticleSource, ConfidenceLevel

_CONFIDENCE_VALUES = frozenset({"alta", "media", "baja", "en_revision"})

_SOURCE_URLS: dict[str, str] = {
    "diario libre": "https://www.diariolibre.com",
    "listín diario": "https://listindiario.com",
    "listin diario": "https://listindiario.com",
    "hoy": "https://hoy.com.do",
    "acento": "https://acento.com.do",
    "el nuevo diario": "https://elnuevodiario.com.do",
    "somos pueblo": "https://somospueblo.com",
}

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def is_valid_slug(slug: str) -> bool:
    return bool(slug) and len(slug) <= 120 and bool(_SLUG_RE.match(slug))


def _split_content(content: str) -> tuple[str, list[str]]:
    text = (content or "").strip()
    if not text:
        return "", []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        paragraphs = [text]
    summary = paragraphs[0]
    body = paragraphs[1:] if len(paragraphs) > 1 else paragraphs
    return summary, body


def _read_time(content: str) -> str:
    words = len((content or "").split())
    minutes = max(1, round(words / 200))
    return f"{minutes} min"


def _parse_sources(raw: str | None) -> list[ArticleSource]:
    if not raw or not str(raw).strip():
        return []
    names = [part.strip() for part in str(raw).split(",") if part.strip()]
    sources: list[ArticleSource] = []
    for name in names:
        url = _SOURCE_URLS.get(name.casefold(), "#")
        sources.append(ArticleSource(name=name, url=url))
    return sources


def _confidence(value: Any) -> ConfidenceLevel:
    if isinstance(value, str) and value in _CONFIDENCE_VALUES:
        return value  # type: ignore[return-value]
    return "en_revision"


def row_to_article(row: dict[str, Any]) -> Article:
    content = row.get("content") or ""
    summary, body = _split_content(content)
    category = (row.get("category") or "").strip() or "General"
    return Article(
        slug=row["slug"],
        category=category,
        title=row.get("title") or "",
        summary=summary,
        body=body,
        image=row.get("image_url") or None,
        imageAlt=None,
        imageCaption=None,
        readTime=_read_time(content),
        confidence=_confidence(row.get("confidence")),
        sources=_parse_sources(row.get("sources")),
        date=row.get("date") or row.get("created_at") or "",
        perspectives=None,
    )
