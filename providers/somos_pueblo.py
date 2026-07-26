from bs4 import BeautifulSoup
from crawl4ai.models import CrawlResult

from providers.base import BaseNewsProvider


class SomosPuebloProvider(BaseNewsProvider):
    base_url = "https://somospueblo.com"
    source = "Somos Pueblo"
    css_selector = ".wpb_wrapper"

    def get_author(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if not html:
            return result.metadata.get("author") or "Sin Autor"

        soup = BeautifulSoup(html, "html.parser")
        author_el = soup.select_one("a.tdb-author-name")
        if author_el and author_el.get_text(strip=True):
            return author_el.get_text(strip=True)

        return result.metadata.get("author") or "Sin Autor"

    def get_category(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, "html.parser")
            category_el = soup.select_one("a.tdb-entry-category")
            if category_el:
                return category_el.get_text(strip=True)
        return result.metadata.get("category") or "Sin Categoría"

    def get_date(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, "html.parser")
            date_el = soup.select_one("time.entry-date, time.td-module-date")
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
            title_el = soup.select_one("h1.tdb-title-text")
            if title_el:
                return title_el.get_text(strip=True)
        return result.metadata.get("title") or "Sin Título"

    def get_content(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, "html.parser")
            content_el = soup.select_one("div.tdb_single_content")
            if content_el:
                return content_el.get_text(strip=True).replace("- Anuncio -", "")
        return result.markdown

    def is_valid_url(self, url: str) -> bool:
        if not url.startswith(self.base_url):
            return False

        ignored_keywords = [
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
