import os
import sys
from pathlib import Path
from typing import Annotated

# mcp CLI loads this file by path; ensure the repo root is importable.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mcp.server.fastmcp import FastMCP
from mcp.types import Completion, PromptReference
from pydantic import Field
from starlette.requests import Request
from starlette.responses import HTMLResponse

from common.config import (
    DEFAULT_DAYS_BACK,
    DEFAULT_LIST_DAYS_BACK,
    DEFAULT_LIST_STORIES_LIMIT,
    DEFAULT_QUERY_LIMIT,
    MAX_DAYS_BACK,
    MAX_QUERY_LIMIT,
    MAX_TOPIC_LENGTH,
)
from common.sources import NewsSource
from mcp_app.auth import load_auth_from_env
from mcp_app.landing import render_landing_html
from mcp_app.prompt import run_get_last_week
from mcp_app.resources import (
    get_source_frontpage,
    get_verified_resource,
    list_sources_json,
)
from mcp_app.tools import (
    run_get_story,
    run_get_verified_article,
    run_list_stories,
    run_list_verified_articles,
    run_search_articles,
    run_search_story,
    run_search_verified_articles,
)

MCP_HOST = os.environ.get("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.environ.get("MCP_PORT", "7000"))
MCP_TRANSPORT = os.environ.get("MCP_TRANSPORT", "stdio")

_auth_settings, _token_verifier = load_auth_from_env()

mcp = FastMCP(
    "multi-source-news-verification-api",
    host=MCP_HOST,
    port=MCP_PORT,
    auth=_auth_settings,
    token_verifier=_token_verifier,
)


@mcp.custom_route("/", methods=["GET"])
async def landing_page(_request: Request) -> HTMLResponse:
    return HTMLResponse(render_landing_html())


@mcp.tool(
    name="search_articles",
    description="Semantic search across all Dominican news articles",
)
def search_articles(
    query: Annotated[
        str,
        Field(
            description='Search query or question (e.g. "reforma fiscal", "apagones").',
            max_length=MAX_TOPIC_LENGTH,
        ),
    ],
    limit: Annotated[
        int,
        Field(
            description="Maximum articles to return.",
            ge=1,
            le=MAX_QUERY_LIMIT,
        ),
    ] = DEFAULT_QUERY_LIMIT,
    days_back: Annotated[
        int,
        Field(
            description="Only include articles from the last N days (by published date).",
            ge=0,
            le=MAX_DAYS_BACK,
        ),
    ] = DEFAULT_DAYS_BACK,
    source: Annotated[
        NewsSource | None,
        Field(description='Optional outlet filter (e.g. "Acento", "Listin Diario").'),
    ] = None,
) -> str:
    """Semantic RAG search over Dominican news (Spanish-friendly embeddings)."""
    return run_search_articles(query, limit, days_back, source)


@mcp.tool(
    name="search_story",
    description="Search news stories and return matching stories with their articles",
)
def search_story(
    query: Annotated[
        str,
        Field(
            description='Story search query (e.g. "reforma fiscal", "apagones").',
            max_length=MAX_TOPIC_LENGTH,
        ),
    ],
    limit: Annotated[
        int,
        Field(
            description="Maximum stories to return.",
            ge=1,
            le=MAX_QUERY_LIMIT,
        ),
    ] = DEFAULT_QUERY_LIMIT,
    days_back: Annotated[
        int,
        Field(
            description="Only include stories with at least one article from the last N days.",
            ge=0,
            le=MAX_DAYS_BACK,
        ),
    ] = DEFAULT_DAYS_BACK,
    source: Annotated[
        NewsSource | None,
        Field(description='Optional outlet filter (e.g. "Acento", "Listin Diario").'),
    ] = None,
) -> str:
    """Semantic search over story descriptions; returns each story with member articles."""
    return run_search_story(query, limit, days_back, source)


@mcp.tool(
    name="list_stories",
    description=(
        "List recent news stories/clusters in compact form "
        "(description, sources, headlines). Use get_story for full content."
    ),
)
def list_stories(
    days_back: Annotated[
        int,
        Field(
            description=(
                "Only include stories with at least one article from the last N days "
                "(rolling window by published date)."
            ),
            ge=0,
            le=MAX_DAYS_BACK,
        ),
    ] = DEFAULT_LIST_DAYS_BACK,
    limit: Annotated[
        int,
        Field(
            description="Maximum stories to return.",
            ge=1,
            le=MAX_QUERY_LIMIT,
        ),
    ] = DEFAULT_LIST_STORIES_LIMIT,
    source: Annotated[
        NewsSource | None,
        Field(description='Optional outlet filter (e.g. "Acento", "Listin Diario").'),
    ] = None,
) -> str:
    """Browse recent story clusters without a semantic query."""
    return run_list_stories(days_back, limit, source)


@mcp.tool(
    name="get_story",
    description=(
        "Get one news story/cluster by STORY_ID with full member articles "
        "(source, date, headline, URL, content)."
    ),
)
def get_story(
    story_id: Annotated[
        str,
        Field(
            description="Story/cluster id from list_stories or search_story (STORY_ID).",
            max_length=MAX_TOPIC_LENGTH,
        ),
    ],
) -> str:
    """Return full member articles for a single story cluster."""
    return run_get_story(story_id)


@mcp.tool(
    name="list_verified_articles",
    description=(
        "List recent synthesized (verified) articles in compact form "
        "(title, date, status, confidence, cluster_id, slug)."
    ),
)
def list_verified_articles(
    days_back: Annotated[
        int,
        Field(
            description=(
                "Only include verified articles from the last N days "
                "(rolling window by article date)."
            ),
            ge=0,
            le=MAX_DAYS_BACK,
        ),
    ] = DEFAULT_LIST_DAYS_BACK,
    limit: Annotated[
        int,
        Field(
            description="Maximum verified articles to return.",
            ge=1,
            le=MAX_QUERY_LIMIT,
        ),
    ] = DEFAULT_LIST_STORIES_LIMIT,
    status: Annotated[
        str | None,
        Field(description='Optional status filter (e.g. "draft", "published").'),
    ] = None,
) -> str:
    """Browse recent verified articles without a semantic query."""
    return run_list_verified_articles(days_back, limit, status)


@mcp.tool(
    name="get_verified_article",
    description=(
        "Get one synthesized (verified) article by CLUSTER_ID with full body, "
        "sources, status, and confidence metadata when available."
    ),
)
def get_verified_article(
    cluster_id: Annotated[
        str,
        Field(
            description=(
                "Cluster id from list_verified_articles or search_verified_articles "
                "(CLUSTER_ID)."
            ),
            max_length=MAX_TOPIC_LENGTH,
        ),
    ],
) -> str:
    """Return one verified article by cluster id."""
    return run_get_verified_article(cluster_id)


@mcp.tool(
    name="search_verified_articles",
    description=(
        "Semantic search over synthesized (verified) article content "
        "(title + body in verified_index)."
    ),
)
def search_verified_articles(
    query: Annotated[
        str,
        Field(
            description='Search query or question (e.g. "reforma fiscal").',
            max_length=MAX_TOPIC_LENGTH,
        ),
    ],
    limit: Annotated[
        int,
        Field(
            description="Maximum verified articles to return.",
            ge=1,
            le=MAX_QUERY_LIMIT,
        ),
    ] = DEFAULT_QUERY_LIMIT,
    days_back: Annotated[
        int,
        Field(
            description="Only include articles from the last N days.",
            ge=0,
            le=MAX_DAYS_BACK,
        ),
    ] = DEFAULT_DAYS_BACK,
    status: Annotated[
        str | None,
        Field(description='Optional status filter (e.g. "draft", "published").'),
    ] = None,
) -> str:
    """Semantic search over verified articles."""
    return run_search_verified_articles(query, limit, days_back, status)


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
def source_frontpage(
    source_id: Annotated[
        str,
        Field(description="News outlet id or name (see news://sources)."),
    ],
) -> str:
    return get_source_frontpage(source_id)


@mcp.resource(
    "news://verified/{cluster_id}",
    name="verified_article",
    description="One synthesized (verified) article as a text document",
    mime_type="text/plain",
)
def verified_article_resource(
    cluster_id: Annotated[
        str,
        Field(description="Cluster id for the verified article."),
    ],
) -> str:
    return get_verified_resource(cluster_id)


@mcp.prompt(
    name="get_last_week",
    description="Last 7 days of articles from a Dominican news outlet",
)
def get_last_week(
    source: Annotated[
        NewsSource,
        Field(description='News outlet name (e.g. "Acento", "Listin Diario").'),
    ],
) -> str:
    return run_get_last_week(source)


@mcp.completion()
async def complete(ref, argument, context):
    """
    Provide argument completion for prompt parameters.

    Suggests news source names as users type the 'source' parameter.
    """
    if isinstance(ref, PromptReference) and ref.name == "get_last_week":
        if argument.name == "source":
            sources = list_sources_json()
            source_names = [src["name"] for src in sources]
            partial = argument.value.lower() if argument.value else ""
            values = [s for s in source_names if s.lower().startswith(partial)]
            return Completion(values=values)
    return None


if __name__ == "__main__":
    allowed = ("stdio", "sse", "streamable-http")
    if MCP_TRANSPORT not in allowed:
        raise SystemExit(
            f"Unknown MCP_TRANSPORT={MCP_TRANSPORT!r}; expected one of {allowed}"
        )
    if MCP_TRANSPORT != "stdio" and _token_verifier is None:
        raise SystemExit(
            "MCP_API_KEY is required for HTTP transports "
            f"(MCP_TRANSPORT={MCP_TRANSPORT!r})"
        )
    print(
        f"Starting MCP server transport={MCP_TRANSPORT} "
        f"host={MCP_HOST} port={MCP_PORT}..."
    )
    mcp.run(transport=MCP_TRANSPORT)
