"""Unit tests for cluster description prompts / DeepInfra client (mocked)."""

from __future__ import annotations

from unittest.mock import patch

import httpx

from preprocessing.describe import (
    DEFAULT_CATEGORY,
    DEFAULT_PLACE,
    build_cluster_prompt,
    call_cluster_llm,
    describe_cluster,
    fallback_cluster_metadata,
    fallback_story_description,
    normalize_category,
    normalize_place,
    parse_cluster_metadata,
)


def _article(
    title: str,
    content: str,
    source: str = "Acento",
    date: str = "2026-01-01",
    category: str | None = None,
):
    return {
        "id": title,
        "title": title,
        "content": content,
        "source": source,
        "date": date,
        "url": f"https://example.com/{title}",
        "category": category,
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
        assert "máximo 800 caracteres" in prompt
        assert "category" in prompt
        assert "place" in prompt

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


class TestParseClusterMetadata:
    def test_parses_json_object(self):
        meta = parse_cluster_metadata(
            '{"description":"Resumen.","category":"Política","place":"Santo Domingo"}'
        )
        assert meta == {
            "description": "Resumen.",
            "category": "Política",
            "place": "SANTO DOMINGO",
        }

    def test_parses_fenced_json(self):
        meta = parse_cluster_metadata(
            '```json\n{"description":"Hechos.","category":"Economía","place":"Santiago"}\n```'
        )
        assert meta is not None
        assert meta["category"] == "Economía"
        assert meta["place"] == "SANTIAGO"

    def test_unknown_category_falls_back(self):
        meta = parse_cluster_metadata(
            '{"description":"Resumen.","category":"Deportes","place":"Nacional"}'
        )
        assert meta is not None
        assert meta["category"] == DEFAULT_CATEGORY

    def test_returns_none_without_description(self):
        assert parse_cluster_metadata('{"category":"Política","place":"Hoy"}') is None


class TestDescribeCluster:
    def test_singleton_uses_cluster_llm(self):
        articles = [_article("Solo", "texto")]
        payload = (
            '{"description":"Resumen singleton.","category":"Sociedad",'
            '"place":"Nacional"}'
        )
        with patch(
            "preprocessing.describe.call_cluster_llm",
            return_value=payload,
        ) as mock_call:
            result = describe_cluster(articles)
        assert result["description"] == "Resumen singleton."
        assert result["category"] == "Sociedad"
        assert result["place"] == "NACIONAL"
        mock_call.assert_called_once()
        assert mock_call.call_args.kwargs["max_chars"] == 800

    def test_empty_uses_fallback(self):
        result = describe_cluster([])
        assert result["description"] == "Historia sin artículos."
        assert result["category"] == DEFAULT_CATEGORY
        assert result["place"] == DEFAULT_PLACE.upper()

    def test_returns_cluster_llm_metadata(self):
        articles = [
            _article("A", "contenido a"),
            _article("B", "contenido b"),
        ]
        payload = (
            '  {"description":"Resumen del cluster.","category":"Cultura",'
            '"place":"Puerto Plata"}  '
        )
        with patch(
            "preprocessing.describe.call_cluster_llm",
            return_value=payload,
        ) as mock_call:
            result = describe_cluster(articles)
        assert result["description"] == "Resumen del cluster."
        assert result["category"] == "Cultura"
        assert result["place"] == "PUERTO PLATA"
        mock_call.assert_called_once()

    def test_truncates_long_cluster_llm_output(self):
        articles = [_article("A", "contenido")]
        payload = (
            '{"description":"' + ("z" * 200) + '","category":"Política",'
            '"place":"Nacional"}'
        )
        with patch(
            "preprocessing.describe.call_cluster_llm",
            return_value=payload,
        ):
            result = describe_cluster(articles, max_chars=40)
        assert len(result["description"]) <= 40
        assert result["description"].endswith("…")

    def test_falls_back_on_cluster_llm_failure(self):
        articles = [
            _article("A", "contenido a", category="Política"),
            _article("B", "contenido b"),
        ]
        with patch(
            "preprocessing.describe.call_cluster_llm",
            side_effect=httpx.ConnectError("refused"),
        ):
            result = describe_cluster(articles)
        assert "A" in result["description"]
        assert "2 artículos" in result["description"]
        assert result["category"] == "Política"
        assert result["place"] == DEFAULT_PLACE.upper()

    def test_falls_back_on_empty_cluster_llm_content(self):
        articles = [_article("A", "contenido a")]
        with patch(
            "preprocessing.describe.call_cluster_llm",
            return_value="",
        ):
            result = describe_cluster(articles)
        assert "A" in result["description"]

    def test_plain_text_uses_defaults_for_category_place(self):
        articles = [_article("A", "contenido a")]
        with patch(
            "preprocessing.describe.call_cluster_llm",
            return_value="Solo un resumen en texto plano.",
        ):
            result = describe_cluster(articles)
        assert result["description"] == "Solo un resumen en texto plano."
        assert result["category"] == DEFAULT_CATEGORY
        assert result["place"] == DEFAULT_PLACE.upper()


class TestNormalizeCategory:
    def test_accent_insensitive(self):
        assert normalize_category("politica") == "Política"
        assert normalize_category("Tecnología") == "Tecnología"


class TestNormalizePlace:
    def test_uppercases_and_collapses_whitespace(self):
        assert normalize_place("Santo Domingo") == "SANTO DOMINGO"
        assert normalize_place("santo\ndomingo") == "SANTO DOMINGO"
        assert normalize_place(None) == "NACIONAL"


class TestFallbackClusterMetadata:
    def test_uses_member_category(self):
        meta = fallback_cluster_metadata(
            [_article("A", "x", category="Economía")]
        )
        assert meta["category"] == "Economía"


class TestCallClusterLlm:
    def test_uses_shared_chat_client(self):
        with patch(
            "preprocessing.describe.chat_completion",
            return_value="Descripción generada",
        ) as mock_chat:
            text = call_cluster_llm(
                "prompt",
                api_key="sk_test",
                model="Qwen/Qwen3.6-35B-A3B",
                max_chars=100,
            )

        assert text == "Descripción generada"
        mock_chat.assert_called_once()
        messages = mock_chat.call_args.args[0]
        kwargs = mock_chat.call_args.kwargs
        assert kwargs["api_key"] == "sk_test"
        assert kwargs["model"] == "Qwen/Qwen3.6-35B-A3B"
        assert kwargs["temperature"] == 0
        assert kwargs["max_tokens"] == 1024
        assert kwargs["max_retries"] == 3
        assert kwargs["chat_template_kwargs"] == {"enable_thinking": False}
        assert "reasoning_effort" not in kwargs
        assert "thinking" not in kwargs
        assert "máximo 100 caracteres" in messages[0]["content"]
        assert "category" in messages[0]["content"]
        assert messages[1]["content"] == "prompt"

    def test_requires_api_key(self):
        with patch("preprocessing.describe.DEEPINFRA_API_KEY", ""):
            try:
                call_cluster_llm("prompt", api_key="")
                raise AssertionError("expected RuntimeError")
            except RuntimeError as exc:
                assert "DEEPINFRA_API_KEY" in str(exc)
