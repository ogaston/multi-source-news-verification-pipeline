"""Shared BeautifulSoup helpers for news provider extraction."""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence

from bs4 import BeautifulSoup, Tag
from crawl4ai.models import CrawlResult

HTML_PARSER = "html.parser"

DEFAULT_ARTICLE_TYPES = frozenset({"Article", "NewsArticle"})
BLOG_ARTICLE_TYPES = frozenset({"Article", "BlogPosting", "NewsArticle"})


def soup_from_result(
    result: CrawlResult,
    *,
    prefer_cleaned: bool = True,
) -> BeautifulSoup | None:
    """Parse HTML from a crawl result, preferring cleaned_html when available."""
    if prefer_cleaned:
        html = result.cleaned_html or result.html
    else:
        html = result.html or result.cleaned_html
    if not html:
        return None
    return BeautifulSoup(html, HTML_PARSER)


def iter_html_variants(
    result: CrawlResult,
    *,
    order: Sequence[str] = ("html", "cleaned_html"),
) -> Iterator[BeautifulSoup]:
    """Yield soups for each available HTML variant in the requested order."""
    for key in order:
        html = result.html if key == "html" else result.cleaned_html
        if html:
            yield BeautifulSoup(html, HTML_PARSER)


def json_ld_nodes(soup: BeautifulSoup) -> Iterator[dict]:
    """Yield dict nodes from JSON-LD script tags, flattening @graph entries."""
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or script.get_text() or "")
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            graph = item.get("@graph")
            if isinstance(graph, list):
                yield from (node for node in graph if isinstance(node, dict))
            yield item


def news_article_ld(
    soup: BeautifulSoup,
    *,
    types: frozenset[str] | None = None,
) -> dict:
    """Return the first JSON-LD node whose @type matches an article schema."""
    allowed = types or DEFAULT_ARTICLE_TYPES
    for node in json_ld_nodes(soup):
        node_types = node.get("@type", [])
        if isinstance(node_types, str):
            node_types = [node_types]
        if any(kind in allowed for kind in node_types):
            return node
    return {}


def ld_field(node: dict, key: str) -> str | None:
    """Normalize a JSON-LD scalar or first list item to a stripped string."""
    value = node.get(key)
    if isinstance(value, list) and value:
        value = value[0]
    if isinstance(value, dict):
        if key == "author" and value.get("name"):
            return str(value["name"]).strip()
        return None
    if value:
        return str(value).strip()
    return None


def first_text(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    """Return stripped text from the first matching selector."""
    for selector in selectors:
        element = soup.select_one(selector)
        if element and element.get_text(strip=True):
            return element.get_text(" ", strip=True)
    return None


def meta_content(soup: BeautifulSoup, property_or_name: str) -> str | None:
    """Read a meta tag by property= or name= attribute."""
    for attr in ("property", "name"):
        element = soup.select_one(f'meta[{attr}="{property_or_name}"]')
        if element and element.get("content"):
            return element["content"].strip()
    return None


def decompose_junk(container: Tag, junk_selectors: str | Sequence[str]) -> None:
    """Remove unwanted elements from a container before text extraction."""
    if isinstance(junk_selectors, str):
        junk_selectors = [junk_selectors]
    for selector in junk_selectors:
        for junk in container.select(selector):
            junk.decompose()


def extract_blocks(
    container: Tag,
    block_selectors: str | Sequence[str] = "p, h2, h3, blockquote, li",
    *,
    junk_phrases: Sequence[str] = (),
    junk_prefixes: Sequence[str] = (),
    direct_children: bool = False,
    paragraph_class: str | None = None,
    fallback_selectors: bool = False,
) -> str:
    """Collect block text from a container, skipping junk phrases and prefixes."""
    if isinstance(block_selectors, str):
        block_selectors = [block_selectors]

    def collect_elements(selector: str) -> list[Tag]:
        if direct_children and paragraph_class:
            elements = container.find_all("p", class_=paragraph_class, recursive=False)
            if elements:
                return elements
            return container.find_all("p", recursive=False)
        return container.select(selector)

    def blocks_from(elements: list[Tag]) -> list[str]:
        collected: list[str] = []
        for element in elements:
            text = element.get_text(" ", strip=True)
            if not text:
                continue
            if any(phrase in text for phrase in junk_phrases):
                continue
            if any(text.startswith(prefix) for prefix in junk_prefixes):
                continue
            collected.append(text)
        return collected

    if fallback_selectors:
        for selector in block_selectors:
            collected = blocks_from(collect_elements(selector))
            if collected:
                return "\n\n".join(collected)
        return ""

    blocks: list[str] = []
    for selector in block_selectors:
        blocks.extend(blocks_from(collect_elements(selector)))
    return "\n\n".join(blocks)
