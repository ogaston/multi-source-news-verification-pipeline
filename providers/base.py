from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.models import CrawlResult


class BaseNewsProvider(ABC):
    base_url: str
    source: str
    css_selector: str

    def __init__(self, crawler: AsyncWebCrawler):
        self.crawler = crawler

    @abstractmethod
    def get_author(self, result: CrawlResult) -> str: ...

    @abstractmethod
    def get_category(self, result: CrawlResult) -> str: ...

    @abstractmethod
    def get_date(self, result: CrawlResult) -> str: ...

    @abstractmethod
    def get_title(self, result: CrawlResult) -> str: ...

    @abstractmethod
    def get_content(self, result: CrawlResult) -> str: ...

    @abstractmethod
    def is_valid_url(self, url: str) -> bool: ...

    def build_article(self, url: str, result: CrawlResult) -> dict:
        return {
            "url": url,
            "source": self.source,
            "title": self.get_title(result),
            "content": self.get_content(result),
            "date": self.get_date(result),
            "author": self.get_author(result),
            "category": self.get_category(result),
            "scraped_at": datetime.now().isoformat(),
        }

    def crawl_config(self) -> CrawlerRunConfig:
        pruning_filter = PruningContentFilter(threshold=0.5, min_word_threshold=30)
        markdown_gen = DefaultMarkdownGenerator(content_filter=pruning_filter)
        return CrawlerRunConfig(
            css_selector=self.css_selector,
            markdown_generator=markdown_gen,
            wait_until="domcontentloaded",
            page_timeout=60000,
        )

    async def run(self, url: str) -> dict | None:
        result = await self.crawler.arun(
            url=url, config=self.crawl_config(), source=self.source
        )
        if result.success and result.markdown:
            return self.build_article(url, result)
        return None

    async def prefetch(self) -> CrawlResult:
        config = CrawlerRunConfig(prefetch=True)
        return await self.crawler.arun(
            url=self.base_url, config=config, source=self.source
        )
