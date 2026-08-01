"""Tests for DeepInfra FLUX cover-image helpers."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

from agents.image_gen import (
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
        "Heated congressional debate in Santo Domingo (Política)"
    )


def test_build_image_prompt_uses_samurai_jack_style():
    prompt = build_image_prompt(
        "Flooding after heavy rains",
        category="Sociedad",
        place="Santiago",
    )
    assert prompt.startswith(
        "Flooding after heavy rains in Santiago (Sociedad) depicted as"
    )
    assert "Samurai Jack" in prompt
    assert "No logos" in prompt


def test_public_image_url():
    assert public_image_url("abc123").endswith("/media/articles/abc123.jpg")


def test_generate_article_image_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr("agents.image_gen.DEEPINFRA_API_KEY", "test-key")
    monkeypatch.setattr(
        "agents.image_gen.PUBLIC_API_URL", "http://localhost:7002"
    )
    raw = b"fake-jpeg-bytes"
    payload = {
        "data": [{"b64_json": base64.b64encode(raw).decode("ascii")}]
    }
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = payload

    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = None
    client.post.return_value = response

    with patch("agents.image_gen.httpx.Client", return_value=client):
        url = generate_article_image(
            article_id="art1",
            title="A protest downtown",
            category="Política",
            place="Santo Domingo",
            images_dir=tmp_path,
        )

    assert url == "http://localhost:7002/media/articles/art1.jpg"
    assert (tmp_path / "art1.jpg").read_bytes() == raw
    posted = client.post.call_args
    assert posted.args[0].endswith("/images/generations")
    assert posted.kwargs["json"]["model"] == "black-forest-labs/FLUX-2-klein-4b"
    assert "Samurai Jack" in posted.kwargs["json"]["prompt"]


def test_generate_article_image_skips_without_api_key(tmp_path, monkeypatch):
    monkeypatch.setattr("agents.image_gen.DEEPINFRA_API_KEY", "")
    url = generate_article_image(
        article_id="art2",
        title="Something",
        images_dir=tmp_path,
    )
    assert url is None
    assert not (tmp_path / "art2.jpg").exists()


def test_generate_article_image_soft_fails_on_http_error(tmp_path, monkeypatch):
    monkeypatch.setattr("agents.image_gen.DEEPINFRA_API_KEY", "test-key")
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = None
    client.post.side_effect = Exception("boom")

    with patch("agents.image_gen.httpx.Client", return_value=client):
        url = generate_article_image(
            article_id="art3",
            title="Something",
            images_dir=tmp_path,
        )
    assert url is None
