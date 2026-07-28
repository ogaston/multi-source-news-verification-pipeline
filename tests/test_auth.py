"""Tests for single-token StaticTokenVerifier."""

from __future__ import annotations

import asyncio

from mcp_app.auth import REQUIRED_SCOPE, StaticTokenVerifier, load_auth_from_env


def test_valid_token():
    verifier = StaticTokenVerifier("secret-token")
    access = asyncio.run(verifier.verify_token("secret-token"))
    assert access is not None
    assert access.client_id == "mcp-client"
    assert REQUIRED_SCOPE in access.scopes


def test_invalid_or_empty_token():
    verifier = StaticTokenVerifier("secret-token")
    assert asyncio.run(verifier.verify_token("wrong")) is None
    assert asyncio.run(verifier.verify_token("")) is None


def test_load_auth_from_env(monkeypatch):
    monkeypatch.setenv("MCP_API_KEY", "my-key")
    monkeypatch.setenv("MCP_DOMAIN", "news.example")
    settings, verifier = load_auth_from_env()
    assert settings is not None
    assert verifier is not None
    assert settings.required_scopes == [REQUIRED_SCOPE]


def test_load_auth_missing_key(monkeypatch):
    monkeypatch.delenv("MCP_API_KEY", raising=False)
    settings, verifier = load_auth_from_env()
    assert settings is None
    assert verifier is None
