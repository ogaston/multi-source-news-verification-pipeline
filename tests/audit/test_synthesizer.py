"""Unit tests for synthesizer prompt and output handling."""

from __future__ import annotations

from unittest.mock import patch

from audit.agents.synthesizer import FINAL_ARTICLE_MAX_CHARS, SYSTEM_PROMPT, run


def test_system_prompt_requires_complete_article_under_limit():
    assert "{max_chars}" in SYSTEM_PROMPT
    assert "never end mid-word" in SYSTEM_PROMPT
    assert "Do not cut the text off" in SYSTEM_PROMPT
    assert "Do NOT start the body with a location or dateline" in SYSTEM_PROMPT


def test_run_does_not_hard_truncate_long_output():
    long_article = "Título\n\n" + ("palabra " * 400)
    assert len(long_article) > FINAL_ARTICLE_MAX_CHARS

    with patch("audit.agents.synthesizer.invoke_llm", return_value=long_article) as mock_llm:
        result = run({"story": "Historia", "judgment": "Keep facts"})

    mock_llm.assert_called_once()
    assert result["article"] == long_article.strip()
    assert set(result) == {"article"}
    assert not result["article"].endswith("…")
    assert mock_llm.call_args.args[1]["max_chars"] == FINAL_ARTICLE_MAX_CHARS
