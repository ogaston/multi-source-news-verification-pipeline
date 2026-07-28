"""Tests for query_topic input clamping (no Chroma required)."""

from __future__ import annotations

from common.config import MAX_DAYS_BACK, MAX_QUERY_LIMIT, MAX_TOPIC_LENGTH
from common.indexing import RetrievedChunk
import mcp_app.tools as tools


def test_clamps_limit_days_back_and_topic(monkeypatch):
    captured: dict = {}

    def fake_retrieve(topic: str, n_results: int):
        captured["topic"] = topic
        captured["n_results"] = n_results
        return [
            RetrievedChunk(
                article_id="a",
                text="chunk",
                score=0.9,
                url="https://example.com/a",
                source="Hoy",
                title="T",
                date="2099-01-01T00:00:00+00:00",
                chunk_index=0,
            )
        ]

    def fake_filter(*args, **kwargs):
        captured["limit"] = kwargs["limit"]
        captured["date_threshold"] = kwargs["date_threshold"]
        return []

    monkeypatch.setattr(tools, "retrieve_chunks", fake_retrieve)
    monkeypatch.setattr(tools, "filter_ranked_chunks", fake_filter)

    long_topic = "x" * (MAX_TOPIC_LENGTH + 100)
    result = tools.run_query_topic(long_topic, limit=10_000, days_back=10_000)

    # Empty after filter still returns a message; topic in message is truncated.
    assert long_topic not in result
    assert ("x" * MAX_TOPIC_LENGTH) in result
    assert captured["limit"] == MAX_QUERY_LIMIT
    assert captured["topic"] == "x" * MAX_TOPIC_LENGTH

    from datetime import datetime, timezone

    age = datetime.now(timezone.utc) - captured["date_threshold"]
    assert abs(age.days - MAX_DAYS_BACK) <= 1
