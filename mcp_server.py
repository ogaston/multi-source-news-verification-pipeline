from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from config import DEFAULT_DAYS_BACK, DEFAULT_QUERY_LIMIT
from resources import get_source_frontpage, list_sources_json
from sources import NewsSource
from tools import run_query_topic

MCP_HOST = os.environ.get("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.environ.get("MCP_PORT", "8000"))
MCP_TRANSPORT = os.environ.get("MCP_TRANSPORT", "stdio")

mcp = FastMCP("dominican_news_repository", host=MCP_HOST, port=MCP_PORT)


@mcp.tool(
    name="query_topic",
    description="Search dominican news for a given topic",
    tags=["news", "search", "topic"],
    meta={
        "author": "Omar Gaston",
        "version": "1.0.0",
        "source": "https://github.com/ogaston/dominican-news-mcp",
    },
    output_type=str,
)
def query_topic(
    topic: str,
    limit: int = DEFAULT_QUERY_LIMIT,
    days_back: int = DEFAULT_DAYS_BACK,
    source: NewsSource | None = None,
) -> str:
    """
    Semantic RAG search over Dominican news (Spanish-friendly embeddings).

    Args:
        topic: Conceptual topic or question (e.g. "reforma fiscal", "apagones").
        limit: Maximum articles to return.
        days_back: Only include articles from the last N days (by published date).
        source: Optional outlet name filter (e.g. "Acento", "Listin Diario").
    """
    return run_query_topic(topic, limit, days_back, source)


@mcp.resource(
    "news://sources",
    name="sources",
    description="Catalog of Dominican news outlets",
    mime_type="application/json",
)
def sources_resource():
    return list_sources_json()


@mcp.resource(
    "news://{source_id}/frontpage",
    name="source_frontpage",
    description="Last 1 day of articles for a news outlet as a text document",
    mime_type="text/plain",
)
def source_frontpage(source_id: str) -> str:
    return get_source_frontpage(source_id)


if __name__ == "__main__":
    allowed = ("stdio", "sse", "streamable-http")
    if MCP_TRANSPORT not in allowed:
        raise SystemExit(
            f"Unknown MCP_TRANSPORT={MCP_TRANSPORT!r}; expected one of {allowed}"
        )
    print(
        f"Starting MCP server transport={MCP_TRANSPORT} "
        f"host={MCP_HOST} port={MCP_PORT}..."
    )
    mcp.run(transport=MCP_TRANSPORT)
