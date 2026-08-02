from crawl4ai.models import CrawlResult

from common.sources import NewsSource
from ingestion.utils.base import BaseNewsProvider
from ingestion.utils.html_utils import (
    first_text,
    iter_html_variants,
    meta_content,
    soup_from_result,
)


class SomosPuebloProvider(BaseNewsProvider):
    base_url = "https://somospueblo.com"
    source = NewsSource.SOMOS_PUEBLO
    # TagDiv puts title/author/date outside the content block; crawl4ai's
    # css_selector replaces result.html, so scope to the whole article.
    css_selector = "article"

    def get_author(self, result: CrawlResult) -> str:
        for soup in iter_html_variants(result):
            author = first_text(soup, ["a.tdb-author-name"])
            if author:
                return author

            author_meta = meta_content(soup, "author")
            if author_meta:
                return author_meta

        return result.metadata.get("author") or "Sin Autor"

    def get_category(self, result: CrawlResult) -> str:
        for soup in iter_html_variants(result):
            category = first_text(soup, ["a.tdb-entry-category"])
            if category:
                return category

            section = meta_content(soup, "article:section")
            if section:
                return section

        return result.metadata.get("category") or "Sin Categoría"

    def get_date(self, result: CrawlResult) -> str:
        for soup in iter_html_variants(result):
            published = meta_content(soup, "article:published_time")
            if published:
                return published

            date_el = soup.select_one("time.entry-date, time.td-module-date")
            if date_el:
                dt = date_el.get("datetime")
                if dt:
                    return dt.strip()
                text = date_el.get_text(strip=True)
                if text:
                    return text

            og_date = meta_content(soup, "og:article:published_time")
            if og_date:
                return og_date

        return (
            result.metadata.get("date")
            or result.metadata.get("og:article:published_time")
            or "Sin Fecha"
        )

    def get_title(self, result: CrawlResult) -> str:
        for soup in iter_html_variants(result):
            title = first_text(soup, ["h1.tdb-title-text"])
            if title:
                return title

            og_title = meta_content(soup, "og:title")
            if og_title:
                return og_title

        return result.metadata.get("title") or "Sin Título"

    def get_content(self, result: CrawlResult) -> str:
        soup = soup_from_result(result)
        if soup:
            content_el = soup.select_one("div.tdb_single_content")
            if content_el:
                return content_el.get_text(strip=True).replace("- Anuncio -", "")
        return result.markdown

    def is_valid_url(self, url: str) -> bool:
        if not url.startswith(self.base_url):
            return False

        ignored_keywords = [
            "/odebrecht/",
            "/moral-valores-y-civica/",
            "/caricaturas-y-memes/",
            "/arte-y-cultura/",
            "/author/",
            "/locales/",
            "/economia/",
            "/dominicano-sin-unidad-no-hay-patria/",
            "/costa-norte/",
            "/portada/",
            "/efemerides-patrias/",
            "/tecnologia/",
            "/un-dia-como-hoy/",
            "/point-of-view/",
            "/conoce-a-tus-representantes/",
            "/internacionales/",
            "/envia-tu-denuncia/",
            "/deportes/",
            "/puntos-de-vista/",
            "/youtube/",
            "/medio-ambiente/",
            "/puntos-de-vista/",
            "/actualidad/",
            "/editorial/",
            "/sobre-nosotros/",
            "/mareo/",
        ]
        return not any(keyword in url for keyword in ignored_keywords)
