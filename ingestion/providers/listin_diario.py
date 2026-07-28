import re

from bs4 import BeautifulSoup
from crawl4ai.models import CrawlResult

from common.sources import NewsSource
from ingestion.providers.base import BaseNewsProvider


class ListinDiarioProvider(BaseNewsProvider):
    base_url = "https://listindiario.com"
    source = NewsSource.LISTIN_DIARIO
    css_selector = "article.c-detail"

    def get_author(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, "html.parser")
            author_el = soup.select_one("span.c-detail__author__name")
            if author_el and author_el.get_text(strip=True):
                return author_el.get_text(strip=True)

        return result.metadata.get("author") or "Sin Autor"

    def get_category(self, result: CrawlResult) -> str:
        for html in (result.html, result.cleaned_html):
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            category_el = soup.select_one(".c-menu-section a")
            if category_el and category_el.get_text(strip=True):
                return category_el.get_text(strip=True)
        return result.metadata.get("category") or "Sin Categoría"

    def get_date(self, result: CrawlResult) -> str:
        for html in (result.html, result.cleaned_html):
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            meta_date = soup.select_one('meta[property="article:published_time"]')
            if meta_date and meta_date.get("content"):
                return meta_date["content"].strip()

            date_el = soup.select_one("time.c-detail__date")
            if date_el:
                dt = date_el.get("datetime")
                if dt:
                    return dt.strip()
                text = date_el.get_text(strip=True)
                if text:
                    return text

        return (
            result.metadata.get("date")
            or result.metadata.get("og:article:published_time")
            or "Sin Fecha"
        )

    def get_title(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, "html.parser")
            title_el = soup.select_one("h1.c-detail__title")
            if title_el:
                return title_el.get_text(strip=True)
        return result.metadata.get("title") or "Sin Título"

    def get_content(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, "html.parser")
            content_el = soup.select_one("div.c-detail__body")
            if content_el:
                for junk in content_el.select(
                    ".c-add, .c-detail__share, .c-detail__tags, "
                    ".c-detail__comments, .c-detail__tepuedeinteresar, "
                    ".c-detail__mostread, .c-detail__bio, "
                    "style, script, iframe, aside, nav"
                ):
                    junk.decompose()

                paragraphs = [
                    p.get_text(" ", strip=True)
                    for p in content_el.select("p")
                    if p.get_text(strip=True)
                    and "Recibe en tu correo" not in p.get_text()
                    and "Suscríbete" not in p.get_text()
                ]
                if paragraphs:
                    return "\n\n".join(paragraphs)

                return content_el.get_text("\n", strip=True)
        return result.markdown

    def is_valid_url(self, url: str) -> bool:
        if not url.startswith(self.base_url):
            return False

        if not re.search(r"/\d{8}/[^/]+_\d+\.html(?:\?|$)", url):
            return False

        ignored_keywords = [
            "/autor/",
            "/tag/",
            "/tags/",
            "/page/",
            "/buscar",
            "/search",
            "/login",
            "/registro",
            "/suscrib",
            "/newsletters",
            "/clasificados/",
            "/obituarios/",
            "/horoscopo/",
            "/edicion-impresa/",
            "/galerias/",
            "/podcast/",
            "/videos/",
            "/wp-content/",
            "/files/",
            "/contacto",
            "/aviso-legal",
            "/politica-de-privacidad",
        ]
        return not any(keyword in url for keyword in ignored_keywords)
