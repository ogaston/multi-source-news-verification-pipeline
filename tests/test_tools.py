"""Tests for query_topic input clamping (no Chroma required)."""

from __future__ import annotations

from unittest.mock import MagicMock

import tools
from config import MAX_DAYS_BACK, MAX_QUERY_LIMIT, MAX_TOPIC_LENGTH


def test_clamps_limit_days_back_and_topic(monkeypatch):
    captured: dict = {}

    mock_collection = MagicMock()
    mock_collection.query.return_value = {"ids": [[]], "metadatas": [[]]}
    monkeypatch.setattr(tools, "get_vector_collection", lambda: mock_collection)

    def fake_filter(*args, **kwargs):
        captured["limit"] = kwargs["limit"]
        captured["date_threshold"] = kwargs["date_threshold"]
        return []

    monkeypatch.setattr(tools, "filter_ranked_ids", fake_filter)

    # Force a non-empty ids path so filter_ranked_ids is called with clamped values.
    mock_collection.query.return_value = {
        "ids": [["a"]],
        "metadatas": [[{"source": "Hoy", "date": "2099-01-01T00:00:00+00:00"}]],
    }

    long_topic = "x" * (MAX_TOPIC_LENGTH + 100)
    result = tools.run_query_topic(long_topic, limit=10_000, days_back=10_000)

    # Empty after filter still returns a message; topic in message is truncated.
    assert long_topic not in result
    assert ("x" * MAX_TOPIC_LENGTH) in result
    assert captured["limit"] == MAX_QUERY_LIMIT

    # days_back clamped: threshold should be roughly now - MAX_DAYS_BACK
    from datetime import datetime, timezone

    age = datetime.now(timezone.utc) - captured["date_threshold"]
    assert abs(age.days - MAX_DAYS_BACK) <= 1

    # Chroma query used truncated topic
    called_topic = mock_collection.query.call_args.kwargs["query_texts"][0]
    assert called_topic == "x" * MAX_TOPIC_LENGTH
