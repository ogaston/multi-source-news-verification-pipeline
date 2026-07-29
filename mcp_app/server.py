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
from mcp_app.prompt import run_get_last_week
from mcp_app.resources import get_source_frontpage, list_sources_json
from mcp_app.tools import (
    run_get_story,
    run_list_stories,
    run_search_articles,
    run_search_story,
)

MCP_HOST = os.environ.get("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.environ.get("MCP_PORT", "8000"))
MCP_TRANSPORT = os.environ.get("MCP_TRANSPORT", "stdio")
LANDING_HTML_PATH = Path(__file__).resolve().parent / "static" / "index.html"

_auth_settings, _token_verifier = load_auth_from_env()

mcp = FastMCP(
    "dominican_news_repository",
    host=MCP_HOST,
    port=MCP_PORT,
    auth=_auth_settings,
    token_verifier=_token_verifier,
)


@mcp.custom_route("/", methods=["GET"])
async def landing_page(_request: Request) -> HTMLResponse:
    return HTMLResponse(LANDING_HTML_PATH.read_text(encoding="utf-8"))


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
