"""Shared DeepInfra HTTP and chat-completion helpers."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Mapping, Sequence
from typing import Any

import httpx

from common.config import DEEPINFRA_API_KEY, DEEPINFRA_BASE_URL, DEEPINFRA_MODEL

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BASE_SECONDS = 2.0
_RETRY_WAIT_RE = re.compile(
    r"(?:try again in|retry after)\s*([\d.]+)\s*(?:s|sec(?:ond)?s?)",
    re.IGNORECASE,
)


def retry_wait_seconds(
    response: httpx.Response,
    attempt: int,
    *,
    retry_base_seconds: float = DEFAULT_RETRY_BASE_SECONDS,
) -> float:
    """Return a server-provided retry delay or an exponential fallback."""
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            pass

    match = _RETRY_WAIT_RE.search(response.text or "")
    if match:
        return float(match.group(1)) + 0.5
    return retry_base_seconds * (2 ** (attempt - 1))


def post_json(
    url: str,
    payload: Mapping[str, Any],
    *,
    api_key: str | None = None,
    timeout: float = 120.0,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_base_seconds: float = DEFAULT_RETRY_BASE_SECONDS,
) -> Any:
    """POST JSON to DeepInfra with shared auth, status, and 429 retry handling."""
    key = api_key if api_key is not None else DEEPINFRA_API_KEY
    if not key:
        raise RuntimeError("DEEPINFRA_API_KEY is not set")
    if max_retries < 1:
        raise ValueError("max_retries must be at least 1")

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=timeout) as client:
        for attempt in range(1, max_retries + 1):
            response = client.post(url, json=dict(payload), headers=headers)
            if response.status_code == 429 and attempt < max_retries:
                wait = retry_wait_seconds(
                    response,
                    attempt,
                    retry_base_seconds=retry_base_seconds,
                )
                logger.warning(
                    "DeepInfra rate limit; retrying in %.1fs (attempt %s/%s)",
                    wait,
                    attempt,
                    max_retries,
                )
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()

    raise RuntimeError("DeepInfra request exhausted retries")


def extract_chat_content(body: Any) -> str:
    """Extract and normalize the first assistant message from a chat response."""
    if not isinstance(body, Mapping):
        return ""
    choices = body.get("choices")
    if not isinstance(choices, Sequence) or isinstance(choices, (str, bytes)):
        return ""
    if not choices or not isinstance(choices[0], Mapping):
        return ""
    message = choices[0].get("message")
    if not isinstance(message, Mapping):
        return ""
    return str(message.get("content") or "").strip()


def chat_completion(
    messages: Sequence[Mapping[str, Any]],
    *,
    api_key: str | None = None,
    model: str = DEEPINFRA_MODEL,
    timeout: float = 120.0,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_url: str = DEEPINFRA_BASE_URL,
    **options: Any,
) -> str:
    """Call DeepInfra's OpenAI-compatible chat endpoint and return its content."""
    payload = {
        "model": model,
        **options,
        "messages": [dict(message) for message in messages],
    }
    body = post_json(
        f"{base_url.rstrip('/')}/chat/completions",
        payload,
        api_key=api_key,
        timeout=timeout,
        max_retries=max_retries,
    )
    return extract_chat_content(body)
