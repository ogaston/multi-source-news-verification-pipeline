"""Map DB verified_articles rows to public Article responses."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from api.schemas import Article, ArticleSlug, ArticleSource, ConfidenceLevel

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
_CATEGORY_NAMES = {
    "politica": "Política",
    "economia": "Economía",
    "clima": "Clima",
    "tecnologia": "Tecnología",
    "sociedad": "Sociedad",
    "cultura": "Cultura",
}


def is_valid_slug(slug: str) -> bool:
    return bool(slug) and len(slug) <= 120 and bool(_SLUG_RE.match(slug))


def category_slug(category: str) -> str:
    normalized = unicodedata.normalize("NFKD", category or "")
    ascii_category = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_category.casefold()).strip("-")


def category_name(slug: str) -> str | None:
    return _CATEGORY_NAMES.get(slug)


def _iso_datetime(value: Any) -> str:
    if not value:
        return ""
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


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
    """Parse JSON [{name, url}] or legacy comma-separated outlet names."""
    if not raw or not str(raw).strip():
        return []
    text = str(raw).strip()
    if text.startswith("["):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, list):
            sources: list[ArticleSource] = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()
                if not name:
                    continue
                url = str(item.get("url") or "").strip()
                if not url:
                    url = _SOURCE_URLS.get(name.casefold(), "#")
                sources.append(ArticleSource(name=name, url=url))
            if sources:
                return sources
    names = [part.strip() for part in text.split(",") if part.strip()]
    return [
        ArticleSource(name=name, url=_SOURCE_URLS.get(name.casefold(), "#"))
        for name in names
    ]


def _confidence(value: Any) -> ConfidenceLevel:
    if isinstance(value, str) and value in _CONFIDENCE_VALUES:
        return value  # type: ignore[return-value]
    return "en_revision"


def row_to_article(row: dict[str, Any]) -> Article:
    content = row.get("content") or ""
    summary, body = _split_content(content)
    category = (row.get("category") or "").strip() or "General"
    cluster_size = row.get("cluster_size")
    try:
        cluster_size_int = int(cluster_size) if cluster_size is not None else None
    except (TypeError, ValueError):
        cluster_size_int = None
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
        publishedAt=_iso_datetime(row.get("date") or row.get("created_at")),
        perspectives=None,
        clusterSize=cluster_size_int,
    )


def article_to_slug(article: Article) -> ArticleSlug:
    return ArticleSlug(
        slug=article.slug,
        category=article.category,
        categorySlug=category_slug(article.category),
        publishedAt=article.publishedAt,
    )
