"""Render the MCP HTTP landing page."""

from __future__ import annotations

import os
from html import escape
from pathlib import Path

LANDING_HTML_PATH = Path(__file__).resolve().parent / "static" / "index.html"


def render_landing_html() -> str:
    """Render the landing page with the currently configured shared token."""
    api_key = escape(os.environ.get("MCP_API_KEY", "").strip())
    return LANDING_HTML_PATH.read_text(encoding="utf-8").replace(
        "{{MCP_API_KEY}}",
        api_key,
    )
