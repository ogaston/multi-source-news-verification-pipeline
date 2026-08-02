"""Unit tests for internally composed database query predicates."""

from __future__ import annotations

import common.db as db


def _capture_queries(monkeypatch):
    calls: list[tuple[str, dict]] = []

    def fake_query_db(sql, params=None):
        calls.append((sql, params or {}))
        return []

    monkeypatch.setattr(db, "query_db", fake_query_db)
    return calls


def test_fetch_unprocessed_articles_composes_time_predicates(monkeypatch):
    calls = _capture_queries(monkeypatch)

    db.fetch_unprocessed_articles(
        limit=7,
        day_start="2026-08-01T00:00:00",
        day_end="2026-08-02T00:00:00",
        lookback_hours=3,
    )
    db.fetch_unprocessed_articles(limit=8, lookback_hours=3)
    db.fetch_unprocessed_articles(limit=9)

    assert len(calls) == 3
    assert ":day_start" in calls[0][0] and ":day_end" in calls[0][0]
    assert "scraped_threshold" not in calls[0][0]
    assert calls[0][1] == {
        "limit": 7,
        "day_start": "2026-08-01T00:00:00",
        "day_end": "2026-08-02T00:00:00",
    }
    assert ":scraped_threshold" in calls[1][0]
    assert calls[1][1]["limit"] == 8
    assert "scraped_threshold" in calls[1][1]
    assert ":day_start" not in calls[2][0]
    assert ":scraped_threshold" not in calls[2][0]
    assert calls[2][1] == {"limit": 9}


def test_fetch_filtered_lists_keep_values_in_named_binds(monkeypatch):
    calls = _capture_queries(monkeypatch)
    unsafe_value = "x' OR TRUE --"

    db.fetch_published_articles(limit=4, category=unsafe_value)
    db.fetch_verified_articles("2026-08-01", status=unsafe_value, limit=5)
    db.fetch_recent_clusters("2026-08-01", source=unsafe_value, limit=6)

    assert len(calls) == 3
    for sql, params in calls:
        assert unsafe_value not in sql
        assert unsafe_value in params.values()
    assert "LOWER(:category)" in calls[0][0]
    assert ":status" in calls[1][0]
    assert "a.source = :source" in calls[2][0]


def test_fetch_filtered_lists_omit_optional_predicates(monkeypatch):
    calls = _capture_queries(monkeypatch)

    db.fetch_published_articles(limit=4)
    db.fetch_verified_articles("2026-08-01", limit=5)
    db.fetch_recent_clusters("2026-08-01", limit=6)

    assert len(calls) == 3
    assert ":category" not in calls[0][0]
    assert ":status" not in calls[1][0]
    assert ":source" not in calls[2][0]
    assert calls[0][1] == {"limit": 4}
    assert calls[1][1] == {"date_threshold": "2026-08-01", "limit": 5}
    assert calls[2][1] == {"date_threshold": "2026-08-01", "limit": 6}


def test_fetch_clusters_by_description_preserves_result_shapes(monkeypatch):
    rows = [
        {
            "cluster_id": "cluster-1",
            "description": "Description",
            "created_at": "2026-08-01",
        }
    ]
    calls: list[str] = []

    def fake_query_db(sql, params=None):
        calls.append(sql)
        return rows

    monkeypatch.setattr(db, "query_db", fake_query_db)

    assert db.fetch_clusters_by_description(has_description=True) == rows
    assert db.fetch_clusters_by_description(has_description=False) == ["cluster-1"]
    assert len(calls) == 2
    assert "description IS NOT NULL" in calls[0]
    assert "description IS NULL" in calls[1]


def test_cluster_bulk_inserts_share_named_bind_execution(monkeypatch):
    executions: list[tuple[str, list[dict]]] = []

    class Connection:
        def execute(self, statement, params):
            executions.append((str(statement), params))

    class Transaction:
        def __enter__(self):
            return Connection()

        def __exit__(self, *_args):
            return None

    class Engine:
        def begin(self):
            return Transaction()

    monkeypatch.setattr(db, "get_engine", Engine)

    db.insert_topic_cluster_rows([])
    db.insert_topic_cluster_rows([("cluster-1", "article-1", "2026-08-01")])
    db.insert_clusters([("cluster-1", "Description", "2026-08-01")])

    assert len(executions) == 2
    assert ":cluster_id" in executions[0][0]
    assert executions[0][1] == [
        {
            "cluster_id": "cluster-1",
            "article_id": "article-1",
            "created_at": "2026-08-01",
        }
    ]
    assert ":description" in executions[1][0]
    assert executions[1][1] == [
        {
            "cluster_id": "cluster-1",
            "description": "Description",
            "created_at": "2026-08-01",
        }
    ]
