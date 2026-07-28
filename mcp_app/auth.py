"""Single-token bearer verification for FastMCP (TokenVerifier protocol).

Mirrors the StaticTokenVerifier pattern from FastMCP docs:
https://gofastmcp.com/servers/auth/token-verification
"""

from __future__ import annotations

import os
import secrets

from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

REQUIRED_SCOPE = "news:read"


class StaticTokenVerifier:
    """Accept one shared API token from ``MCP_API_KEY``."""

    def __init__(self, token: str, *, client_id: str = "mcp-client") -> None:
        self._token = token
        self._client_id = client_id

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token or not secrets.compare_digest(token, self._token):
            return None
        return AccessToken(
            token=token,
            client_id=self._client_id,
            scopes=[REQUIRED_SCOPE],
        )


def load_auth_from_env() -> tuple[AuthSettings, StaticTokenVerifier] | tuple[None, None]:
    """Return FastMCP auth settings + verifier when ``MCP_API_KEY`` is set."""
    token = os.environ.get("MCP_API_KEY", "").strip()
    if not token:
        return None, None

    domain = os.environ.get("MCP_DOMAIN", "localhost").strip() or "localhost"
    base = os.environ.get("MCP_RESOURCE_URL", f"http://{domain}").rstrip("/")
    settings = AuthSettings(
        issuer_url=AnyHttpUrl(base),
        resource_server_url=AnyHttpUrl(base),
        required_scopes=[REQUIRED_SCOPE],
    )
    return settings, StaticTokenVerifier(token)
