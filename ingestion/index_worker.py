"""Isolated Chroma indexing worker — must not import Crawl4AI."""

from __future__ import annotations

import json
import sys


def run_index_batch(articles: list[dict]) -> None:
    from common.indexing import index_article

    for article in articles:
        article_id = str(article.get("id") or "")
        try:
            chunks = index_article(article)
            print(
                f"[ingest] indexed {article_id[:12]}… chunks={chunks}",
                flush=True,
            )
        except Exception as exc:
            print(f"[ingest] index failed {article_id}: {exc}", flush=True)


def main() -> None:
    raw = sys.stdin.read()
    articles = json.loads(raw) if raw.strip() else []
    if not isinstance(articles, list):
        raise SystemExit("index worker expected a JSON list of articles")
    run_index_batch(articles)


if __name__ == "__main__":
    main()
