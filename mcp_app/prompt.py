"""MCP prompt implementations (logic only; decorators live in mcp_app.server)."""

from __future__ import annotations

from common.sources import NewsSource
from mcp_app.utils import format_frontpage, load_source_articles

LAST_WEEK_DAYS = 7


def run_get_last_week(source: NewsSource) -> str:
    rows = load_source_articles(source, days_back=LAST_WEEK_DAYS)
    if not rows:
        return f"No articles found for {source.value} in the last {LAST_WEEK_DAYS} days."

    return format_frontpage(source, rows, days_back=LAST_WEEK_DAYS)
