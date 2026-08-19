from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys

from crawl4ai import AsyncWebCrawler

from common.config import DATA_DIR, DEFAULT_URL_LIMIT
from common.db import (
    article_fingerprint,
    article_key_exists,
    existing_urls,
    init_db,
    save_news,
)
from common.sources import NewsSource
from ingestion.pipeline import prepare_article
from ingestion.providers import NEWS_PROVIDERS


def save_in_json(content: dict, url: str) -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    safe = re.sub(r"[^\w.\-]+", "_", url)
    path = os.path.join(DATA_DIR, f"{safe}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(content, f, indent=4, ensure_ascii=False)
    print(f"Saved content to json file: {path}")
    return path


async def discover_news(crawler: AsyncWebCrawler, source: NewsSource) -> list[str]:
    """Discover news from a target URL"""
    provider = NEWS_PROVIDERS[source](crawler)

    print(f"Discovering news from source: {source} from URL: {provider.base_url}")

    result = await provider.prefetch()

    discovered_urls: set[str] = set()
    if result.links:
        internal_links = result.links.get("internal", [])
        print(f"Found {len(internal_links)} internal links")

        for link in internal_links:
            href = link.get("href")
            if href and provider.is_valid_url(href):
                discovered_urls.add(href)

    print(f"Found {len(discovered_urls)} discovered URLs")
    return list(discovered_urls)


async def scrape_news(
    crawler: AsyncWebCrawler, url: str, source: NewsSource
) -> dict | None:
    """Scrape news from a URL"""
    print(f"Scraping news from source: {source} from URL: {url}")
    provider = NEWS_PROVIDERS[source](crawler)
    return await provider.run(url)


def _index_record(prepared: dict, news_id: str) -> dict:
    return {
        "id": news_id,
        "url": prepared["url"],
        "source": prepared.get("source"),
        "title": prepared["title"],
        "content": prepared["content"],
        "date": prepared["date"],
    }


def index_saved_articles(articles: list[dict]) -> None:
    """
    Index saved articles in a fresh interpreter.

    Ingest was SIGSEGVing (exit 139) when HuggingFace/PyTorch/Chroma loaded
    in the same process as Crawl4AI's Chromium. A subprocess that only
    imports the index worker keeps those native stacks apart.
    """
    if not articles:
        return
    print(
        f"[ingest] indexing {len(articles)} articles in isolated process...",
        flush=True,
    )
    result = subprocess.run(
        [sys.executable, "-m", "ingestion.index_worker"],
        input=json.dumps(articles),
        text=True,
        check=False,
    )
    if result.returncode:
        print(
            f"[ingest] isolated indexer exited {result.returncode}",
            flush=True,
        )
    else:
        print("[ingest] indexing complete", flush=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover and ingest Dominican news into PostgreSQL + Chroma."
    )
    parser.add_argument(
        "--source",
        action="append",
        choices=sorted(s.value for s in NewsSource),
        help="Outlet to scrape (repeatable). Default: all providers.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_URL_LIMIT,
        help=f"Max URLs per source (default: {DEFAULT_URL_LIMIT}).",
    )
    parser.add_argument(
        "--write-json",
        action="store_true",
        help=f"Also write debug JSON under {DATA_DIR}/ (off by default).",
    )
    return parser.parse_args(argv)


async def run_ingest(
    sources: list[NewsSource],
    limit: int,
    write_json: bool = False,
) -> None:
    init_db()
    pending_index: list[dict] = []

    async with AsyncWebCrawler() as crawler:
        for source in sources:
            discovered_urls = await discover_news(crawler, source)
            known = existing_urls(discovered_urls)
            new_urls = [url for url in discovered_urls if url not in known]
            skipped = len(discovered_urls) - len(new_urls)
            to_scrape = new_urls[:limit]
            print(
                f"{source}: {len(discovered_urls)} discovered, "
                f"{skipped} already in DB, scraping {len(to_scrape)}"
            )

            for url in to_scrape:
                article = await scrape_news(crawler, url, source)
                if not article:
                    print(f"Failed to scrape news from URL: {url}")
                    continue

                prepared, reason = prepare_article(article)
                if reason:
                    print(f"Skipped {url}: {reason}")
                    continue

                assert prepared is not None
                key = article_fingerprint(
                    prepared.get("source"),
                    prepared["title"],
                    prepared["date"],
                )
                if article_key_exists(key):
                    print(f"Skipped {url}: duplicate article_key")
                    continue

                if write_json:
                    save_in_json(prepared, url)
                saved = save_news(prepared)
                if saved is None:
                    print(f"Skipped {url}: duplicate article_key")
                    continue
                print(f"[ingest] saved {source.value} {url}", flush=True)
                pending_index.append(_index_record(prepared, saved))

    print("Scraping complete")
    index_saved_articles(pending_index)
    print("Done")


async def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    sources = (
        [NewsSource(s) for s in args.source]
        if args.source
        else list(NEWS_PROVIDERS.keys())
    )
    await run_ingest(sources=sources, limit=args.limit, write_json=args.write_json)


if __name__ == "__main__":
    asyncio.run(main())
