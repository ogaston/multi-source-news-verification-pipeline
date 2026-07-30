"""Shared DeepSeek chat model for story-audit agents."""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from openai import APIStatusError, RateLimitError

load_dotenv()
# Prefer agents/.env when present (overrides root .env for agent runs).
load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MAX_TOKENS = int(os.environ.get("DEEPSEEK_MAX_TOKENS", "4096"))
MAX_RETRIES = int(os.environ.get("DEEPSEEK_MAX_RETRIES", "5"))
DEFAULT_RETRY_WAIT = float(os.environ.get("DEEPSEEK_RETRY_WAIT", "8"))

_RETRY_WAIT_RE = re.compile(r"try again in ([\d.]+)\s*s", re.IGNORECASE)


def get_llm(*, temperature: float = 0) -> ChatOpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise SystemExit(
            "DEEPSEEK_API_KEY is required (set it in agents/.env or the environment)"
        )
    return ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=api_key,
        base_url=DEEPSEEK_BASE_URL,
        temperature=temperature,
        max_tokens=DEEPSEEK_MAX_TOKENS,
    )


def response_text(response: Any) -> str:
    """Normalize AIMessage content to plain text (str or block list)."""
    content = response.content
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") in (None, "text"):
                parts.append(str(block.get("text") or ""))
        return "\n".join(part for part in parts if part).strip()
    return str(content or "").strip()


def _retry_wait_seconds(exc: Exception, attempt: int) -> float:
    match = _RETRY_WAIT_RE.search(str(exc))
    if match:
        return float(match.group(1)) + 0.5
    return DEFAULT_RETRY_WAIT * (2 ** (attempt - 1))


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, APIStatusError) and exc.status_code in (408, 409, 429, 500, 502, 503, 504):
        return True
    return False


def invoke_llm(prompt: ChatPromptTemplate, inputs: dict[str, Any]) -> str:
    """Invoke a prompt chain with retries on rate limits / empty responses."""
    chain = prompt | get_llm()
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = chain.invoke(inputs)
            text = response_text(response)
            if text:
                return text
            if attempt >= MAX_RETRIES:
                break
            wait = DEFAULT_RETRY_WAIT
            print(
                f"[deepseek] empty response; retrying in {wait:.1f}s "
                f"(attempt {attempt}/{MAX_RETRIES})",
                flush=True,
            )
            time.sleep(wait)
        except (RateLimitError, APIStatusError) as exc:
            last_exc = exc
            if not _is_retryable(exc) or attempt >= MAX_RETRIES:
                raise
            wait = _retry_wait_seconds(exc, attempt)
            print(
                f"[deepseek] rate/limit error; retrying in {wait:.1f}s "
                f"(attempt {attempt}/{MAX_RETRIES})",
                flush=True,
            )
            time.sleep(wait)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(
        f"DeepSeek returned empty content after {MAX_RETRIES} attempts "
        f"(model={DEEPSEEK_MODEL}). Try raising DEEPSEEK_MAX_TOKENS or "
        f"switching to deepseek-chat."
    )
