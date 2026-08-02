import json
from datetime import datetime

from audit.agents.analyzer import parse_analysis
from audit.image_gen import generate_article_image
from common.db import (
    fetch_cluster,
    insert_clusters,
    insert_verified_article,
    mark_cluster_processed,
    update_verified_article_image,
)
from common.taxonomy import normalize_category, normalize_place

_DATELINE_SKIP_PLACES = frozenset({"NACIONAL", "INTERNACIONAL"})


def split_article(article: str) -> tuple[str, str]:
    """Split synthesizer output into title (first non-empty line) and body."""
    lines = [line.strip() for line in (article or "").splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return ("(sin título)", "")
    title = lines[0].lstrip("#").strip() or "(sin título)"
    if title.startswith("**") and title.endswith("**") and len(title) > 4:
        title = title[2:-2].strip()
    body = "\n\n".join(lines[1:]).strip()
    return title, body


def article_sources(articles: list[dict]) -> str | None:
    """Serialize unique outlets with first seen article URL as JSON."""
    by_name: dict[str, str] = {}
    for article in articles:
        name = (article.get("source") or "").strip()
        url = (article.get("url") or "").strip()
        if not name or name in by_name:
            continue
        by_name[name] = url
    if not by_name:
        return None
    payload = [{"name": name, "url": by_name[name]} for name in sorted(by_name)]
    return json.dumps(payload, ensure_ascii=False)


def article_date(articles: list[dict]) -> str | None:
    dates = [(item.get("date") or "").strip() for item in articles]
    dates = [date for date in dates if date]
    return max(dates) if dates else None


def _parse_story_field(field: str, story: str) -> str | None:
    prefix = f"{field}:"
    for line in story.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip() or None
    return None


def parse_story_id_from_text(story: str) -> str | None:
    return _parse_story_field("STORY_ID", story)


def parse_sources_from_text(story: str) -> str | None:
    return _parse_story_field("SOURCES", story)


def resolve_article_metadata(
    cluster_id: str,
    *,
    category: str | None = None,
    place: str | None = None,
) -> tuple[str, str]:
    """Resolve category/place from cluster metadata (never raw outlet sections)."""
    cluster = fetch_cluster(cluster_id)
    raw_category = (category or "").strip()
    raw_place = (place or "").strip()
    if cluster:
        if not raw_category:
            raw_category = (cluster.get("category") or "").strip()
        if not raw_place:
            raw_place = (cluster.get("place") or "").strip()
    return normalize_category(raw_category or None), normalize_place(raw_place or None)


def prepend_place_dateline(body: str, place: str | None) -> str:
    """Prepend a Dominican-style dateline when place is present."""
    text = (body or "").strip()
    location = normalize_place(place) if (place or "").strip() else ""
    if not location or location in _DATELINE_SKIP_PLACES:
        return text
    dateline = f"{location}.—"
    if text.upper().startswith(f"{location}."):
        return text
    if not text:
        return dateline
    return f"{dateline} {text}"


def persist_verified(
    *,
    cluster_id: str,
    result: dict,
    articles: list[dict] | None = None,
    sources: str | None = None,
    category: str | None = None,
    place: str | None = None,
) -> str:
    title, body = split_article(result.get("article") or "")
    if not body:
        body = title
    members = articles or []
    resolved_category, resolved_place = resolve_article_metadata(
        cluster_id,
        category=category,
        place=place,
    )
    body = prepend_place_dateline(body, resolved_place)
    analysis = parse_analysis(result.get("analysis"))
    article_id = insert_verified_article(
        cluster_id=cluster_id,
        title=title,
        content=body,
        image_url=None,
        date=article_date(members),
        sources=sources if sources is not None else article_sources(members),
        category=resolved_category,
        place=resolved_place,
        status="published",
        confidence=analysis["confidence"],
        confidence_score=analysis["confidence_score"],
        source_scores=analysis["source_scores"],
        audit_json=analysis["audit_json"],
    )
    mark_cluster_processed(cluster_id)
    return article_id


def attach_cover_image(
    *,
    article_id: str,
    title: str,
    category: str | None = None,
    place: str | None = None,
) -> str | None:
    """Generate a cover image and persist its URL. Soft-fails on errors."""
    try:
        image_url = generate_article_image(
            article_id=article_id,
            title=title,
            category=category,
            place=place,
        )
    except Exception as exc:
        print(f"[image-gen] unexpected error for {article_id}: {exc}", flush=True)
        return None
    if not image_url:
        return None
    try:
        update_verified_article_image(article_id, image_url)
    except Exception as exc:
        print(f"[image-gen] failed to update image_url for {article_id}: {exc}", flush=True)
        return None
    return image_url


def ensure_cluster(cluster_id: str) -> dict:
    cluster = fetch_cluster(cluster_id)
    if cluster is None:
        insert_clusters(
            [(cluster_id, "Example / file-based audit", datetime.now().isoformat())]
        )
        cluster = fetch_cluster(cluster_id)
    return cluster or {}
