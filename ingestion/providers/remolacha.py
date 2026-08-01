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


def _article_data(soup: BeautifulSoup) -> dict:
    for node in _json_ld_nodes(soup):
        types = node.get("@type", [])
        if isinstance(types, str):
            types = [types]
        if any(kind in {"Article", "BlogPosting", "NewsArticle"} for kind in types):
            return node
    return {}


def _post_category(soup: BeautifulSoup) -> str | None:
    post = soup.select_one('#content > div[id^="post-"].post')
    if not post:
        return None
    for class_name in post.get("class", []):
        if class_name.startswith("category-"):
            return class_name.removeprefix("category-").replace("-", " ").title()
    return None


def _timestamp_date(soup: BeautifulSoup) -> str | None:
    timestamp = soup.select_one(".timestamp")
    if not timestamp:
        return None
    parent = timestamp.find_parent("a")
    date_text = timestamp.get_text(" ", strip=True)
    match = re.fullmatch(r"([A-Za-záéíóú]+)\s+(\d{1,2}),\s*(\d{4})", date_text)
    if not match:
        return date_text or None

    months = {
        "enero": 1,
        "febrero": 2,
        "marzo": 3,
        "abril": 4,
        "mayo": 5,
        "junio": 6,
        "julio": 7,
        "agosto": 8,
        "septiembre": 9,
        "octubre": 10,
        "noviembre": 11,
        "diciembre": 12,
    }
    month = months.get(match.group(1).casefold())
    if month is None:
        return date_text

    hour = minute = 0
    time_text = parent.get("title", "") if parent else ""
    time_match = re.fullmatch(r"(\d{1,2}):(\d{2})\s*([ap])m", time_text.casefold())
    if time_match:
        hour = int(time_match.group(1)) % 12
        if time_match.group(3) == "p":
            hour += 12
        minute = int(time_match.group(2))

    return (
        f"{int(match.group(3)):04}-{month:02}-{int(match.group(2)):02}"
        f"T{hour:02}:{minute:02}:00-04:00"
    )


def _extract_blocks(container) -> str:
    junk_phrases = (
        "(Seguir leyendo",
        "Read more ›",
        "⬆️(clic en foto pa’ ver el video)",
        "Dímelo, ¿qué opinas?",
        "Tú sí eres “ponemano”",
    )
    blocks = []
    for element in container.select("p, h2, h3, blockquote, li"):
        text = element.get_text(" ", strip=True)
        if text and not any(phrase in text for phrase in junk_phrases):
            blocks.append(text)
    return "\n\n".join(blocks)


class RemolachaProvider(BaseNewsProvider):
    base_url = "https://remolacha.net"
    source = NewsSource.REMOLACHA
    css_selector = "div.post.type-post.hentry"

    def get_author(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, HTML_PARSER)
            author_el = soup.select_one(".post-meta .author.vcard .fn")
            if author_el and author_el.get_text(strip=True):
                return author_el.get_text(" ", strip=True)

            meta_author = soup.select_one('meta[name="author"]')
            if meta_author and meta_author.get("content"):
                return meta_author["content"].strip()

            author = _article_data(soup).get("author")
            if isinstance(author, list) and author:
                author = author[0]
            if isinstance(author, dict) and author.get("name"):
                return str(author["name"]).strip()

        return result.metadata.get("author") or "Sin Autor"

    def get_category(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, HTML_PARSER)
            category_el = soup.select_one('.post-data a[rel~="category"]')
            if category_el and category_el.get_text(strip=True):
                return category_el.get_text(" ", strip=True).lstrip("*").strip()

            section = _article_data(soup).get("articleSection")
            if isinstance(section, list) and section:
                section = section[0]
            if section:
                return str(section).lstrip("*").strip()

            post_category = _post_category(soup)
            if post_category:
                return post_category

        return result.metadata.get("category") or "Sin Categoría"

    def get_date(self, result: CrawlResult) -> str:
        for html in (result.html, result.cleaned_html):
            if not html:
                continue
            soup = BeautifulSoup(html, HTML_PARSER)
            meta_date = soup.select_one('meta[property="article:published_time"]')
            if meta_date and meta_date.get("content"):
                return meta_date["content"].strip()

            published = _article_data(soup).get("datePublished")
            if published:
                return str(published).strip()

            timestamp_date = _timestamp_date(soup)
            if timestamp_date:
                return timestamp_date

        return (
            result.metadata.get("date")
            or result.metadata.get("og:article:published_time")
            or "Sin Fecha"
        )

    def get_title(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, HTML_PARSER)
            title_el = soup.select_one("h1.post-title")
            if title_el and title_el.get_text(strip=True):
                return title_el.get_text(" ", strip=True)

            meta_title = soup.select_one('meta[property="og:title"]')
            if meta_title and meta_title.get("content"):
                return meta_title["content"].strip()

            headline = _article_data(soup).get("headline")
            if headline:
                return str(headline).strip()

        return result.metadata.get("title") or "Sin Título"

    def get_content(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, HTML_PARSER)
            content_el = soup.select_one("div.post-entry")
            if content_el:
                for junk in content_el.select(
                    ".navigation, .comments-link, #respond, .comments-fb, "
                    ".breadcrumb-list, #widgets, #remo-overlay, "
                    'a[href*="#more-"], script, style'
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
        if parsed.netloc not in {"remolacha.net", "www.remolacha.net"}:
            return False

        return bool(
            re.fullmatch(
                r"/\d{4}/(?:0[1-9]|1[0-2])/"
                r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?/?",
                parsed.path.lower(),
            )
        )
