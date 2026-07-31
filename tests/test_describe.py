"""Unit tests for cluster description prompts / DeepSeek client (mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from preprocessing.describe import (
    DEEPSEEK_CHAT_URL,
    build_cluster_prompt,
    call_deepseek,
    describe_cluster,
    fallback_story_description,
)


def _article(title: str, content: str, source: str = "Acento", date: str = "2026-01-01"):
    return {
        "id": title,
        "title": title,
        "content": content,
        "source": source,
        "date": date,
        "url": f"https://example.com/{title}",
    }


class TestBuildClusterPrompt:
    def test_includes_titles_and_sources(self):
        prompt = build_cluster_prompt(
            [
                _article("Titular uno", "Cuerpo uno"),
                _article("Titular dos", "Cuerpo dos", source="Hoy"),
            ]
        )
        assert "Titular uno" in prompt
        assert "Titular dos" in prompt
        assert "Acento" in prompt
        assert "Hoy" in prompt
        assert "Descripción breve en español (máximo 800 caracteres)" in prompt

    def test_truncates_long_content(self):
        long_body = "x" * 500
        prompt = build_cluster_prompt(
            [_article("T", long_body), _article("U", "short")],
            max_chars=50,
        )
        assert "…" in prompt
        assert "x" * 500 not in prompt
        assert "máximo 50 caracteres" in prompt


class TestFallbackStoryDescription:
    def test_empty_articles(self):
        assert fallback_story_description([]) == "Historia sin artículos."

    def test_single_article(self):
        text = fallback_story_description([_article("Titular", "Cuerpo corto")])
        assert "Titular" in text
        assert "Acento" in text
        assert "Cuerpo corto" in text

    def test_multiple_articles_note_count(self):
        text = fallback_story_description(
            [_article("A", "uno"), _article("B", "dos")]
        )
        assert "2 artículos" in text

    def test_respects_max_chars(self):
        text = fallback_story_description(
            [_article("Titular largo", "y" * 400)],
            max_chars=60,
        )
        assert len(text) <= 60
        assert text.endswith("…")


class TestDescribeCluster:
    def test_singleton_uses_deepseek(self):
        articles = [_article("Solo", "texto")]
        with patch(
            "preprocessing.describe.call_deepseek",
            return_value="Resumen singleton.",
        ) as mock_call:
            result = describe_cluster(articles)
        assert result == "Resumen singleton."
        mock_call.assert_called_once()
        assert mock_call.call_args.kwargs["max_chars"] == 800

    def test_empty_uses_fallback(self):
        assert describe_cluster([]) == "Historia sin artículos."

    def test_returns_deepseek_text(self):
        articles = [
            _article("A", "contenido a"),
            _article("B", "contenido b"),
        ]
        with patch(
            "preprocessing.describe.call_deepseek",
            return_value="  Resumen del cluster.  ",
        ) as mock_call:
            result = describe_cluster(articles)
        assert result == "Resumen del cluster."
        mock_call.assert_called_once()

    def test_truncates_long_deepseek_output(self):
        articles = [_article("A", "contenido")]
        with patch(
            "preprocessing.describe.call_deepseek",
            return_value="z" * 200,
        ):
            result = describe_cluster(articles, max_chars=40)
        assert len(result) <= 40
        assert result.endswith("…")

    def test_falls_back_on_deepseek_failure(self):
        articles = [
            _article("A", "contenido a"),
            _article("B", "contenido b"),
        ]
        with patch(
            "preprocessing.describe.call_deepseek",
            side_effect=httpx.ConnectError("refused"),
        ):
            result = describe_cluster(articles)
        assert "A" in result
        assert "2 artículos" in result

    def test_falls_back_on_empty_deepseek_content(self):
        articles = [_article("A", "contenido a")]
        with patch(
            "preprocessing.describe.call_deepseek",
            return_value="",
        ):
            result = describe_cluster(articles)
        assert "A" in result


class TestCallDeepseek:
    def test_posts_chat_payload(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": " Descripción generada "}}]
        }
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.post.return_value = mock_response

        with patch("preprocessing.describe.httpx.Client", return_value=mock_client):
            text = call_deepseek(
                "prompt",
                api_key="sk_test",
                model="deepseek-chat",
                max_chars=100,
            )

        assert text == "Descripción generada"
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert args[0] == DEEPSEEK_CHAT_URL
        assert kwargs["headers"]["Authorization"] == "Bearer sk_test"
        assert kwargs["json"]["model"] == "deepseek-chat"
        assert kwargs["json"]["temperature"] == 0
        assert kwargs["json"]["max_tokens"] == 1024
        assert kwargs["json"]["reasoning_effort"] == "low"
        assert kwargs["json"]["thinking"] == {"type": "disabled"}
        assert "máximo 100 caracteres" in kwargs["json"]["messages"][0]["content"]
        assert kwargs["json"]["messages"][1]["content"] == "prompt"

    def test_requires_api_key(self):
        with patch("preprocessing.describe.DEEPSEEK_API_KEY", ""):
            try:
                call_deepseek("prompt", api_key="")
                raise AssertionError("expected RuntimeError")
            except RuntimeError as exc:
                assert "DEEPSEEK_API_KEY" in str(exc)
