from bs4 import BeautifulSoup
from crawl4ai.models import CrawlResult

from common.sources import NewsSource
from ingestion.providers.base import BaseNewsProvider


class ElNuevoDiarioProvider(BaseNewsProvider):
    base_url = "https://elnuevodiario.com.do"
    source = NewsSource.EL_NUEVO_DIARIO
    css_selector = "article.noticia-detalle"

    def get_author(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, "html.parser")
            author_el = soup.select_one(
                'header.entry-header .entry-meta a[href*="/author/"] b'
            )
            if author_el and author_el.get_text(strip=True):
                return author_el.get_text(strip=True)

            author_link = soup.select_one(
                'header.entry-header .entry-meta a[href*="/author/"]'
            )
            if author_link and author_link.get_text(strip=True):
                return author_link.get_text(strip=True)

        return result.metadata.get("author") or "Sin Autor"

    def get_category(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, "html.parser")
            category_el = soup.select_one("a.section-name")
            if category_el and category_el.get_text(strip=True):
                return category_el.get_text(strip=True)
        return result.metadata.get("category") or "Sin Categoría"

    def get_date(self, result: CrawlResult) -> str:
        # Prefer raw html: cleaned_html often drops <head> meta tags, leaving only
        # Spanish time.entry-date text that normalize_date cannot parse.
        for html in (result.html, result.cleaned_html):
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            meta_date = soup.select_one('meta[property="article:published_time"]')
            if meta_date and meta_date.get("content"):
                return meta_date["content"].strip()

            date_el = soup.select_one("time.entry-date")
            if date_el:
                dt = date_el.get("datetime")
                # Site puts Spanish prose in datetime=; only accept ISO-like values.
                if dt and dt[:1].isdigit():
                    return dt.strip()
                text = date_el.get_text(strip=True)
                if text and text[:1].isdigit():
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
            title_el = soup.select_one("h1.entry-title")
            if title_el:
                return title_el.get_text(strip=True)
        return result.metadata.get("title") or "Sin Título"

    def get_content(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, "html.parser")
            content_el = soup.select_one("div.entry-content")
            if content_el:
                for junk in content_el.select(
                    "#gemini-summary-wrapper, #gemini-loading, "
                    "style, script, [data-beyondwords-player], "
                    ".sharedaddy, .jp-relatedposts"
                ):
                    junk.decompose()

                paragraphs = [
                    p.get_text(" ", strip=True)
                    for p in content_el.select("p")
                    if p.get_text(strip=True)
                    and "Recibe en tu correo" not in p.get_text()
                ]
                if paragraphs:
                    return "\n\n".join(paragraphs)

                return content_el.get_text("\n", strip=True)
        return result.markdown

    def is_valid_url(self, url: str) -> bool:
        if not url.startswith(self.base_url):
            return False

        ignored_keywords = [
            "/author/",
            "/category/",
            "/tag/",
            "/page/",
            "/wp-content/",
            "/wp-admin/",
            "/contactos/",
            "/quienes-somos/",
            "/edicionimpresa/",
            "/documentales/",
            "/podcast/",
            "/programa-podcast/",
            "/encuesta/",
            "/estudio/",
            "/intent/",
            "/politica-de-privacidad/",
            "/condiciones-del-servicio/",
            "/politica-editorial/",
            "/politicas-de-seguridad/",
            "/politica-de-cambios-y-devoluciones/",
            "/trabaja-con-nosotros/",
            "/nacionales/",
            "/internacionales/",
            "/deportes/",
            "/politica/",
            "/economia/",
            "/opinion/",
            "/editorial/",
            "/denuncias/",
            "/buenas-noticias/",
            "/salud/",
            "/viral/",
            "/sociales/",
            "/medio-ambiente/",
            "/sabores/",
            "/new-york/",
            "/novedades/",
            "/mundo-otaku/",
            "/sostenibilidad/",
            "/toga/",
        ]
        return not any(keyword in url for keyword in ignored_keywords)
