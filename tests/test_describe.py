"""Unit tests for cluster description prompts / Ollama client (mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from preprocessing.describe import (
    build_cluster_prompt,
    call_ollama,
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
        assert "Descripción breve en español" in prompt

    def test_truncates_long_content(self):
        long_body = "x" * 500
        prompt = build_cluster_prompt(
            [_article("T", long_body), _article("U", "short")],
            max_chars=50,
        )
        assert "…" in prompt
        assert "x" * 500 not in prompt


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


class TestDescribeCluster:
    def test_singleton_uses_ollama(self):
        articles = [_article("Solo", "texto")]
        with patch(
            "preprocessing.describe.call_ollama",
            return_value="Resumen singleton.",
        ) as mock_call:
            result = describe_cluster(articles)
        assert result == "Resumen singleton."
        mock_call.assert_called_once()

    def test_empty_uses_fallback(self):
        assert describe_cluster([]) == "Historia sin artículos."

    def test_returns_ollama_text(self):
        articles = [
            _article("A", "contenido a"),
            _article("B", "contenido b"),
        ]
        with patch(
            "preprocessing.describe.call_ollama",
            return_value="  Resumen del cluster.  ",
        ) as mock_call:
            result = describe_cluster(articles)
        assert result == "Resumen del cluster."
        mock_call.assert_called_once()

    def test_falls_back_on_ollama_failure(self):
        articles = [
            _article("A", "contenido a"),
            _article("B", "contenido b"),
        ]
        with patch(
            "preprocessing.describe.call_ollama",
            side_effect=httpx.ConnectError("refused"),
        ):
            result = describe_cluster(articles)
        assert "A" in result
        assert "2 artículos" in result


class TestCallOllama:
    def test_posts_chat_payload(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": " Descripción generada "}
        }
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.post.return_value = mock_response

        with patch("preprocessing.describe.httpx.Client", return_value=mock_client):
            text = call_ollama(
                "prompt",
                base_url="http://localhost:11434",
                model="llama3.2",
            )

        assert text == "Descripción generada"
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert args[0] == "http://localhost:11434/api/chat"
        assert kwargs["json"]["model"] == "llama3.2"
        assert kwargs["json"]["stream"] is False
        assert kwargs["json"]["think"] is False
        assert kwargs["json"]["messages"][1]["content"] == "prompt"
