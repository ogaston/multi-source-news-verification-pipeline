"""MCP resource implementations (logic only; decorators live in mcp_app.server)."""

from __future__ import annotations

from common.sources import NewsSource
from mcp_app.tools import run_get_verified_article
from mcp_app.utils import format_frontpage, load_source_articles


def resolve_source_id(source_id: str) -> NewsSource | None:
    key = source_id.strip().upper()
    try:
        return NewsSource[key]
    except KeyError:
        return None


def list_sources_json() -> list[dict[str, str]]:
    return [
        {"id": member.name.lower(), "name": member.value} for member in NewsSource
    ]


def get_source_frontpage(source_id: str) -> str:
    source = resolve_source_id(source_id)
    if source is None:
        known = ", ".join(member.name.lower() for member in NewsSource)
        return f"Unknown source_id: '{source_id}'. Expected one of: {known}."

    rows = load_source_articles(source, days_back=1)
    if not rows:
        return f"No articles found for {source.value} in the last 1 day."

    return format_frontpage(source, rows)


def get_verified_resource(cluster_id: str) -> str:
    return run_get_verified_article(cluster_id)
