"""Ingest must not load Chroma/PyTorch while Crawl4AI Chromium is alive."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import common.db as db
from common.sources import NewsSource
from ingestion import ingestor


def test_save_news_does_not_index(monkeypatch):
    indexed: list[dict] = []

    class FakeResult:
        def fetchone(self):
            return None

    class FakeConn:
        def execute(self, *args, **kwargs):
            return FakeResult()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeEngine:
        def begin(self):
            return FakeConn()

    monkeypatch.setattr(db, "get_engine", lambda: FakeEngine())
    monkeypatch.setattr(db, "now_pipeline_iso", lambda: "2026-08-19T10:00:00")
    monkeypatch.setattr(
        "common.indexing.index_article",
        lambda article: indexed.append(article),
    )

    news_id = db.save_news(
        {
            "url": "https://example.com/a",
            "title": "Titulo",
            "content": "Cuerpo del articulo con suficiente texto.",
            "source": "Acento",
            "date": "2026-08-19T10:00:00",
            "author": "Redaccion",
            "category": "Nacionales",
        }
    )
    assert news_id
    assert indexed == []


def test_index_saved_articles_runs_isolated_worker(monkeypatch):
    calls: list[dict] = []

    def fake_run(cmd, *, input, text, check):
        calls.append({"cmd": cmd, "input": input, "text": text, "check": check})
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(ingestor.subprocess, "run", fake_run)
    articles = [{"id": "abc", "title": "T"}]
    ingestor.index_saved_articles(articles)
    assert len(calls) == 1
    assert calls[0]["cmd"][-2:] == ["-m", "ingestion.index_worker"]
    assert json.loads(calls[0]["input"]) == articles
    assert calls[0]["text"] is True
    assert calls[0]["check"] is False


def test_index_saved_articles_skips_empty(monkeypatch):
    def fail_run(*args, **kwargs):
        raise AssertionError("must not spawn for empty batch")

    monkeypatch.setattr(ingestor.subprocess, "run", fail_run)
    ingestor.index_saved_articles([])


def test_run_ingest_indexes_after_crawler_closes(monkeypatch):
    events: list[str] = []

    class FakeCrawler:
        async def __aenter__(self):
            events.append("crawler_enter")
            return self

        async def __aexit__(self, *args):
            events.append("crawler_exit")

    async def fake_discover(_crawler, source):
        events.append(f"discover:{source.value}")
        return ["https://example.com/a"]

    async def fake_scrape(_crawler, url, source):
        events.append(f"scrape:{url}")
        return {
            "url": url,
            "title": "Titulo valido de prueba",
            "content": "Cuerpo del articulo con suficiente texto para pasar.",
            "source": source.value,
            "date": "2026-08-19T10:00:00",
            "author": "Redaccion",
            "category": "Nacionales",
        }

    monkeypatch.setattr(ingestor, "AsyncWebCrawler", FakeCrawler)
    monkeypatch.setattr(ingestor, "init_db", lambda: events.append("init"))
    monkeypatch.setattr(ingestor, "discover_news", fake_discover)
    monkeypatch.setattr(ingestor, "existing_urls", lambda urls: set())
    monkeypatch.setattr(ingestor, "scrape_news", fake_scrape)
    monkeypatch.setattr(ingestor, "article_key_exists", lambda _key: False)
    monkeypatch.setattr(
        ingestor,
        "save_news",
        lambda prepared: events.append("save") or "news-id-1",
    )
    monkeypatch.setattr(
        ingestor,
        "index_saved_articles",
        lambda articles: events.append(f"index:{len(articles)}"),
    )
    monkeypatch.setattr(
        ingestor,
        "prepare_article",
        lambda article: (article, None),
    )
    monkeypatch.setattr(ingestor, "article_fingerprint", lambda *args: "key")

    asyncio.run(ingestor.run_ingest(sources=[NewsSource.ACENTO], limit=1))

    assert events.index("crawler_exit") < events.index("index:1")
    assert events.index("save") < events.index("crawler_exit")
    assert "crawler_enter" in events


def test_index_worker_source_does_not_import_crawl4ai():
    import inspect

    import ingestion.index_worker as worker

    source = inspect.getsource(worker)
    assert "crawl4ai" not in source


def test_run_index_batch_continues_after_failure(monkeypatch, capsys):
    from ingestion.index_worker import run_index_batch

    calls: list[str] = []

    def fake_index(article):
        calls.append(article["id"])
        if article["id"] == "bad":
            raise RuntimeError("boom")
        return 2

    monkeypatch.setattr("common.indexing.index_article", fake_index)
    run_index_batch([{"id": "bad"}, {"id": "good"}])
    assert calls == ["bad", "good"]
    out = capsys.readouterr().out
    assert "index failed bad: boom" in out
    assert "indexed good" in out
