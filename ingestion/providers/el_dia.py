import re
from urllib.parse import urlparse

from crawl4ai.models import CrawlResult

from common.sources import NewsSource
from ingestion.utils.base import BaseNewsProvider
from ingestion.utils.html_utils import (
    decompose_junk,
    extract_blocks,
    first_text,
    iter_html_variants,
    ld_field,
    meta_content,
    news_article_ld,
    soup_from_result,
)


class ElDiaProvider(BaseNewsProvider):
    base_url = "https://eldia.com.do"
    source = NewsSource.EL_DIA
    css_selector = "main#main-content section.single"

    def get_author(self, result: CrawlResult) -> str:
        soup = soup_from_result(result)
        if soup:
            author = first_text(soup, ['.author-short a[rel="author"]'])
            if author:
                return author

            ld_author = ld_field(news_article_ld(soup), "author")
            if ld_author:
                return ld_author

        return result.metadata.get("author") or "Sin Autor"

    def get_category(self, result: CrawlResult) -> str:
        for soup in iter_html_variants(result, order=("cleaned_html", "html")):
            category = first_text(soup, ['.author-short a[href*="/secciones/"]'])
            if category:
                return category

            section = meta_content(soup, "article:section")
            if section:
                return section

            ld_section = ld_field(news_article_ld(soup), "articleSection")
            if ld_section:
                return ld_section

        return result.metadata.get("category") or "Sin Categoría"

    def get_date(self, result: CrawlResult) -> str:
        for soup in iter_html_variants(result):
            published = meta_content(soup, "article:published_time")
            if published:
                return published

            ld_date = ld_field(news_article_ld(soup), "datePublished")
            if ld_date:
                return ld_date

            date_el = soup.select_one(".single-date time[datetime]")
            if date_el and date_el.get("datetime"):
                return date_el["datetime"].strip()

        return (
            result.metadata.get("date")
            or result.metadata.get("og:article:published_time")
            or "Sin Fecha"
        )

    def get_title(self, result: CrawlResult) -> str:
        soup = soup_from_result(result)
        if soup:
            title = first_text(soup, ["h1.single-title"])
            if title:
                return title

            headline = ld_field(news_article_ld(soup), "headline")
            if headline:
                return headline

            og_title = meta_content(soup, "og:title")
            if og_title:
                return og_title

        return result.metadata.get("title") or "Sin Título"

    def get_content(self, result: CrawlResult) -> str:
        soup = soup_from_result(result)
        if soup:
            content_el = soup.select_one("section.single div.content.pt-3.border-top")
            if content_el:
                decompose_junk(
                    content_el,
                    (
                        ".gpt-ad-slot, .puede-leer-module, "
                        "blockquote.instagram-media, iframe, script, style"
                    ),
                )

                content = extract_blocks(
                    content_el,
                    junk_phrases=(
                        "Puede leer",
                        "Ver esta publicación en Instagram",
                        "Una publicación compartida por",
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
