import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from crawl4ai.models import CrawlResult

from common.sources import NewsSource
from ingestion.utils.base import BaseNewsProvider
from ingestion.utils.html_utils import (
    BLOG_ARTICLE_TYPES,
    decompose_junk,
    extract_blocks,
    first_text,
    iter_html_variants,
    ld_field,
    meta_content,
    news_article_ld,
    soup_from_result,
)

HTML_PARSER = "html.parser"


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


class RemolachaProvider(BaseNewsProvider):
    base_url = "https://remolacha.net"
    source = NewsSource.REMOLACHA
    css_selector = "div.post.type-post.hentry"

    def get_author(self, result: CrawlResult) -> str:
        soup = soup_from_result(result)
        if soup:
            author = first_text(soup, [".post-meta .author.vcard .fn"])
            if author:
                return author

            author_meta = meta_content(soup, "author")
            if author_meta:
                return author_meta

            ld_author = ld_field(news_article_ld(soup, types=BLOG_ARTICLE_TYPES), "author")
            if ld_author:
                return ld_author

        return result.metadata.get("author") or "Sin Autor"

    def get_category(self, result: CrawlResult) -> str:
        soup = soup_from_result(result)
        if soup:
            category = first_text(soup, ['.post-data a[rel~="category"]'])
            if category:
                return category.lstrip("*").strip()

            ld_section = ld_field(news_article_ld(soup, types=BLOG_ARTICLE_TYPES), "articleSection")
            if ld_section:
                return ld_section.lstrip("*").strip()

            post_category = _post_category(soup)
            if post_category:
                return post_category

        return result.metadata.get("category") or "Sin Categoría"

    def get_date(self, result: CrawlResult) -> str:
        for soup in iter_html_variants(result):
            published = meta_content(soup, "article:published_time")
            if published:
                return published

            ld_date = ld_field(news_article_ld(soup, types=BLOG_ARTICLE_TYPES), "datePublished")
            if ld_date:
                return ld_date

            timestamp_date = _timestamp_date(soup)
            if timestamp_date:
                return timestamp_date

        return (
            result.metadata.get("date")
            or result.metadata.get("og:article:published_time")
            or "Sin Fecha"
        )

    def get_title(self, result: CrawlResult) -> str:
        soup = soup_from_result(result)
        if soup:
            title = first_text(soup, ["h1.post-title"])
            if title:
                return title

            og_title = meta_content(soup, "og:title")
            if og_title:
                return og_title

            headline = ld_field(news_article_ld(soup, types=BLOG_ARTICLE_TYPES), "headline")
            if headline:
                return headline

        return result.metadata.get("title") or "Sin Título"

    def get_content(self, result: CrawlResult) -> str:
        soup = soup_from_result(result)
        if soup:
            content_el = soup.select_one("div.post-entry")
            if content_el:
                decompose_junk(
                    content_el,
                    (
                        ".navigation, .comments-link, #respond, .comments-fb, "
                        ".breadcrumb-list, #widgets, #remo-overlay, "
                        'a[href*="#more-"], script, style'
                    ),
                )

                content = extract_blocks(
                    content_el,
                    junk_phrases=(
                        "(Seguir leyendo",
                        "Read more ›",
                        "⬆️(clic en foto pa’ ver el video)",
                        "Dímelo, ¿qué opinas?",
                        "Tú sí eres “ponemano”",
                    ),
                )
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
