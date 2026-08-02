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


class ElCaribeProvider(BaseNewsProvider):
    base_url = "https://www.elcaribe.com.do"
    source = NewsSource.EL_CARIBE
    css_selector = "article.type-post.status-publish"

    def get_author(self, result: CrawlResult) -> str:
        soup = soup_from_result(result)
        if soup:
            author = first_text(soup, [".author.vcard a.url.fn.n"])
            if author:
                return author

            author_meta = meta_content(soup, "author")
            if author_meta:
                return author_meta

            ld_author = ld_field(news_article_ld(soup), "author")
            if ld_author:
                return ld_author

        return result.metadata.get("author") or "Sin Autor"

    def get_category(self, result: CrawlResult) -> str:
        soup = soup_from_result(result)
        if soup:
            category = first_text(soup, ['.cat-links a[rel~="category"]'])
            if category:
                return category

            ld_section = ld_field(news_article_ld(soup), "articleSection")
            if ld_section:
                return ld_section

        return result.metadata.get("category") or "Sin Categoría"

    def get_date(self, result: CrawlResult) -> str:
        for soup in iter_html_variants(result):
            published = meta_content(soup, "article:published_time")
            if published:
                return published

            date_el = soup.select_one("time.entry-date.published[datetime]")
            if date_el and date_el.get("datetime"):
                return date_el["datetime"].strip()

            ld_date = ld_field(news_article_ld(soup), "datePublished")
            if ld_date:
                return ld_date

        return (
            result.metadata.get("date")
            or result.metadata.get("og:article:published_time")
            or "Sin Fecha"
        )

    def get_title(self, result: CrawlResult) -> str:
        soup = soup_from_result(result)
        if soup:
            title = first_text(soup, ["h1.entry-title"])
            if title:
                return title

            og_title = meta_content(soup, "og:title")
            if og_title:
                return og_title

            headline = ld_field(news_article_ld(soup), "headline")
            if headline:
                return headline

        return result.metadata.get("title") or "Sin Título"

    def get_content(self, result: CrawlResult) -> str:
        soup = soup_from_result(result)
        if soup:
            content_el = soup.select_one(".entry-content > .content")
            if content_el:
                decompose_junk(
                    content_el,
                    (
                        ".mmc_ads, .entry-resumen, .elcaribe-simple-player, "
                        ".share, .newsletter-block, script, style, iframe, aside"
                    ),
                )

                content = extract_blocks(
                    content_el,
                    "p.wp-block-paragraph, p, h2, h3, blockquote, li",
                    junk_prefixes=("Le recomendamos leer", "Escuchar artículo"),
                )
                if content:
                    return content
                return content_el.get_text("\n", strip=True)

        return result.markdown

    def is_valid_url(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "www.elcaribe.com.do":
            return False

        path = parsed.path.lower()
        ignored = (
            "/seccion/",
            "/autor/",
            "/tag/",
            "/tags/",
            "/page/",
            "/buscar/",
            "/search/",
            "/newsletter",
            "/wp-admin/",
            "/wp-content/",
            "/wp-includes/",
            "/cdn-cgi/",
            "/feed/",
            "/video/",
            "/videos/",
            "/podcast/",
            "/galeria/",
            "/galerias/",
            "/contacto",
            "/privacidad",
            "/terminos",
            "/edicion-impresa",
        )
        if any(token in path for token in ignored):
            return False

        return bool(re.fullmatch(r"/(?:[a-z0-9-]+/){2,}[a-z0-9-]+/?", path))
