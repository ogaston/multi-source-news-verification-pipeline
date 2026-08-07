"""Tests for DeepInfra FLUX cover-image helpers."""

from __future__ import annotations

import base64
from unittest.mock import patch

from audit.image_gen import (
    build_event_summary,
    build_image_prompt,
    generate_article_image,
    public_image_url,
)


def test_build_event_summary_includes_place_and_category():
    summary = build_event_summary(
        "Heated congressional debate",
        category="Política",
        place="Santo Domingo",
    )
    assert summary == (
        "Contemporary news scene: Heated congressional debate, "
        "set in Santo Domingo, topic Política"
    )


def test_build_image_prompt_uses_samurai_jack_aesthetic_only():
    prompt = build_image_prompt(
        "Flooding after heavy rains",
        category="Sociedad",
        place="Santiago",
    )
    assert prompt.startswith(
        "Contemporary news scene: Flooding after heavy rains, "
        "set in Santiago, topic Sociedad."
    )
    assert "aesthetic of Samurai Jack" in prompt
    assert "do not include Samurai Jack" in prompt
    assert "samurai warriors" in prompt
    assert "no text" in prompt.lower()
    assert "4:3" in prompt
    assert "never depict graphic violence" in prompt
    assert "respectful reference image" in prompt
    assert "sorrowful child" in prompt
    assert "somber woman" in prompt


def test_public_image_url():
    assert public_image_url("abc123").endswith("/media/articles/abc123.jpg")


def test_generate_article_image_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr("audit.image_gen.DEEPINFRA_API_KEY", "test-key")
    monkeypatch.setattr(
        "audit.image_gen.PUBLIC_API_URL", "http://localhost:7002"
    )
    raw = b"fake-jpeg-bytes"
    payload = {
        "data": [{"b64_json": base64.b64encode(raw).decode("ascii")}]
    }
    with patch("audit.image_gen.post_json", return_value=payload) as mock_post:
        url = generate_article_image(
            article_id="art1",
            title="A protest downtown",
            category="Política",
            place="Santo Domingo",
            size="1024x768",
            images_dir=tmp_path,
        )

    assert url == "http://localhost:7002/media/articles/art1.jpg"
    assert (tmp_path / "art1.jpg").read_bytes() == raw
    posted = mock_post.call_args
    assert posted.args[0].endswith("/images/generations")
    assert posted.args[1]["model"] == "black-forest-labs/FLUX-2-klein-4b"
    assert posted.args[1]["size"] == "1024x768"
    assert "aesthetic of Samurai Jack" in posted.args[1]["prompt"]
    assert "samurai warriors" in posted.args[1]["prompt"]
    assert posted.kwargs["api_key"] == "test-key"


def test_generate_article_image_skips_without_api_key(tmp_path, monkeypatch):
    monkeypatch.setattr("audit.image_gen.DEEPINFRA_API_KEY", "")
    url = generate_article_image(
        article_id="art2",
        title="Something",
        images_dir=tmp_path,
    )
    assert url is None
    assert not (tmp_path / "art2.jpg").exists()


def test_generate_article_image_soft_fails_on_http_error(tmp_path, monkeypatch):
    monkeypatch.setattr("audit.image_gen.DEEPINFRA_API_KEY", "test-key")
    with patch("audit.image_gen.post_json", side_effect=Exception("boom")):
        url = generate_article_image(
            article_id="art3",
            title="Something",
            images_dir=tmp_path,
        )
    assert url is None
