import json
import re
from collections.abc import Iterator
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from crawl4ai.models import CrawlResult

from common.sources import NewsSource
from ingestion.providers.base import BaseNewsProvider

HTML_PARSER = "html.parser"


def _json_ld_nodes(soup: BeautifulSoup) -> Iterator[dict]:
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


def _news_article(soup: BeautifulSoup) -> dict:
    for node in _json_ld_nodes(soup):
        types = node.get("@type", [])
        if isinstance(types, str):
            types = [types]
        if any(kind in {"Article", "NewsArticle"} for kind in types):
            return node
    return {}


def _extract_blocks(container) -> str:
    junk_phrases = (
        "Puede leer",
        "Ver esta publicación en Instagram",
        "Una publicación compartida por",
    )
    blocks = []
    for element in container.select("p, h2, h3, li"):
        text = element.get_text(" ", strip=True)
        if text and not any(phrase in text for phrase in junk_phrases):
            blocks.append(text)
    return "\n\n".join(blocks)


class ElDiaProvider(BaseNewsProvider):
    base_url = "https://eldia.com.do"
    source = NewsSource.EL_DIA
    css_selector = "main#main-content section.single"

    def get_author(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, HTML_PARSER)
            author_el = soup.select_one('.author-short a[rel="author"]')
            if author_el and author_el.get_text(strip=True):
                return author_el.get_text(" ", strip=True)

            author = _news_article(soup).get("author")
            if isinstance(author, list) and author:
                author = author[0]
            if isinstance(author, dict) and author.get("name"):
                return str(author["name"]).strip()

        return result.metadata.get("author") or "Sin Autor"

    def get_category(self, result: CrawlResult) -> str:
        for html in (result.cleaned_html, result.html):
            if not html:
                continue
            soup = BeautifulSoup(html, HTML_PARSER)
            category_el = soup.select_one('.author-short a[href*="/secciones/"]')
            if category_el and category_el.get_text(strip=True):
                return category_el.get_text(" ", strip=True)

            meta_section = soup.select_one('meta[property="article:section"]')
            if meta_section and meta_section.get("content"):
                return meta_section["content"].strip()

            section = _news_article(soup).get("articleSection")
            if isinstance(section, list) and section:
                section = section[0]
            if section:
                return str(section).strip()

        return result.metadata.get("category") or "Sin Categoría"

    def get_date(self, result: CrawlResult) -> str:
        for html in (result.html, result.cleaned_html):
            if not html:
                continue
            soup = BeautifulSoup(html, HTML_PARSER)
            meta_date = soup.select_one('meta[property="article:published_time"]')
            if meta_date and meta_date.get("content"):
                return meta_date["content"].strip()

            published = _news_article(soup).get("datePublished")
            if published:
                return str(published).strip()

            date_el = soup.select_one(".single-date time[datetime]")
            if date_el and date_el.get("datetime"):
                return date_el["datetime"].strip()

        return (
            result.metadata.get("date")
            or result.metadata.get("og:article:published_time")
            or "Sin Fecha"
        )

    def get_title(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, HTML_PARSER)
            title_el = soup.select_one("h1.single-title")
            if title_el and title_el.get_text(strip=True):
                return title_el.get_text(" ", strip=True)

            headline = _news_article(soup).get("headline")
            if headline:
                return str(headline).strip()

            meta_title = soup.select_one('meta[property="og:title"]')
            if meta_title and meta_title.get("content"):
                return meta_title["content"].strip()

        return result.metadata.get("title") or "Sin Título"

    def get_content(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, HTML_PARSER)
            content_el = soup.select_one("section.single div.content.pt-3.border-top")
            if content_el:
                for junk in content_el.select(
                    ".gpt-ad-slot, .puede-leer-module, "
                    "blockquote.instagram-media, iframe, script, style"
                ):
                    junk.decompose()

                content = _extract_blocks(content_el)
                if content:
                    return content
                return content_el.get_text("\n", strip=True)

        return result.markdown

    def is_valid_url(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        if parsed.netloc not in {"eldia.com.do", "www.eldia.com.do"}:
            return False

        path = parsed.path.lower()
        ignored = (
            "/author/",
            "/secciones/",
            "/etiquetas/",
            "/page/",
            "/wp-content/",
            "/wp-admin/",
            "/juegos/",
            "/newsletter/",
            "/contacto/",
            "/tito-salcedo/",
        )
        if any(path.startswith(prefix) for prefix in ignored):
            return False

        return bool(re.fullmatch(r"/[a-z0-9]+(?:-[a-z0-9]+)+/?", path))
