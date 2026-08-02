"""Tests for the shared DeepInfra HTTP and chat helpers."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from common.deepinfra_chat import (
    chat_completion,
    extract_chat_content,
    post_json,
    retry_wait_seconds,
)


def _response(
    status_code: int,
    *,
    text: str = "",
    headers: dict[str, str] | None = None,
    json_body: object | None = None,
) -> httpx.Response:
    content = json.dumps(json_body).encode() if json_body is not None else text.encode()
    response = httpx.Response(
        status_code,
        content=content,
        headers=headers,
        request=httpx.Request("POST", "https://example.test"),
    )
    if json_body is not None:
        response.headers["content-type"] = "application/json"
    return response


def test_retry_wait_prefers_retry_after_header():
    response = _response(429, headers={"Retry-After": "1.25"})
    assert retry_wait_seconds(response, 1) == 1.25


def test_retry_wait_parses_deepinfra_message_and_falls_back_exponentially():
    response = _response(429, text="Rate limit reached; try again in 3.5s")
    assert retry_wait_seconds(response, 1) == 4.0
    assert retry_wait_seconds(_response(429), 3) == 8.0


def test_post_json_retries_429_then_returns_json():
    limited = _response(429, headers={"Retry-After": "0.1"})
    success = _response(200, json_body={"ok": True})
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    client.post.side_effect = [limited, success]

    with (
        patch("common.deepinfra_chat.httpx.Client", return_value=client),
        patch("common.deepinfra_chat.time.sleep") as sleep,
    ):
        assert post_json(
            "https://example.test",
            {"hello": "world"},
            api_key="test-key",
        ) == {"ok": True}

    assert client.post.call_count == 2
    assert client.post.call_args.kwargs["headers"]["Authorization"] == "Bearer test-key"
    sleep.assert_called_once_with(0.1)


def test_post_json_stops_after_bounded_retries():
    responses = [_response(429) for _ in range(3)]
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    client.post.side_effect = responses

    with (
        patch("common.deepinfra_chat.httpx.Client", return_value=client),
        patch("common.deepinfra_chat.time.sleep") as sleep,
        pytest.raises(httpx.HTTPStatusError),
    ):
        post_json(
            "https://example.test",
            {},
            api_key="test-key",
            max_retries=3,
        )

    assert client.post.call_count == 3
    assert [call.args[0] for call in sleep.call_args_list] == [2.0, 4.0]


def test_post_json_requires_api_key_before_request():
    with (
        patch("common.deepinfra_chat.DEEPINFRA_API_KEY", ""),
        patch("common.deepinfra_chat.httpx.Client") as client,
        pytest.raises(RuntimeError, match="DEEPINFRA_API_KEY"),
    ):
        post_json("https://example.test", {})
    client.assert_not_called()


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({"choices": [{"message": {"content": "  respuesta  "}}]}, "respuesta"),
        ({"choices": []}, ""),
        ({"choices": [{"message": {}}]}, ""),
        ({"unexpected": True}, ""),
    ],
)
def test_extract_chat_content(body, expected):
    assert extract_chat_content(body) == expected


def test_chat_completion_builds_chat_request():
    with patch(
        "common.deepinfra_chat.post_json",
        return_value={"choices": [{"message": {"content": " elegida "}}]},
    ) as mock_post:
        result = chat_completion(
            [{"role": "user", "content": "elige"}],
            api_key="test-key",
            model="test-model",
            base_url="https://api.example/v1/",
            max_tokens=64,
        )

    assert result == "elegida"
    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.example/v1/chat/completions"
    assert args[1]["model"] == "test-model"
    assert args[1]["max_tokens"] == 64
    assert args[1]["messages"][0]["content"] == "elige"
    assert kwargs["api_key"] == "test-key"
