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

_SPANISH_MONTHS = {
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

# e.g. "sábado, 1 de agosto 2026 | 8:59 am"
_SPANISH_ENTRY_DATE = re.compile(
    r"(?:[a-záéíóú]+),\s*(\d{1,2})\s+de\s+([a-záéíóú]+)\s+(\d{4})"
    r"(?:\s*\|\s*(\d{1,2}):(\d{2})\s*([ap])\.?m\.?)?",
    re.IGNORECASE,
)


def _parse_spanish_entry_date(text: str) -> str | None:
    match = _SPANISH_ENTRY_DATE.fullmatch(text.strip())
    if not match:
        return None

    month = _SPANISH_MONTHS.get(match.group(2).casefold())
    if month is None:
        return None

    hour = minute = 0
    if match.group(4):
        hour = int(match.group(4)) % 12
        if match.group(6).casefold() == "p":
            hour += 12
        minute = int(match.group(5))

    return (
        f"{int(match.group(3)):04}-{month:02}-{int(match.group(1)):02}"
        f"T{hour:02}:{minute:02}:00-04:00"
    )

NON_ARTICLE_PATH_PREFIXES = (
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
)

SECTION_INDEX_PATHS = frozenset(
    {
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
    }
)

ARTICLE_PATH_PATTERN = re.compile(r"/[a-z0-9]+(?:-[a-z0-9]+)+/?")


class ElNuevoDiarioProvider(BaseNewsProvider):
    base_url = "https://elnuevodiario.com.do"
    source = NewsSource.EL_NUEVO_DIARIO
    css_selector = "article.noticia-detalle"

    def get_author(self, result: CrawlResult) -> str:
        soup = soup_from_result(result)
        if soup:
            author = first_text(
                soup,
                [
                    'header.entry-header .entry-meta a[href*="/author/"] b',
                    'header.entry-header .entry-meta a[href*="/author/"]',
                ],
            )
            if author:
                return author

        return result.metadata.get("author") or "Sin Autor"

    def get_category(self, result: CrawlResult) -> str:
        soup = soup_from_result(result)
        if soup:
            category = first_text(soup, ["a.section-name"])
            if category:
                return category
        return result.metadata.get("category") or "Sin Categoría"

    def get_date(self, result: CrawlResult) -> str:
        # Prefer ISO sources; the site often puts Spanish prose in time datetime=.
        for soup in iter_html_variants(result):
            published = meta_content(soup, "article:published_time")
            if published:
                return published

            ld_date = ld_field(news_article_ld(soup), "datePublished")
            if ld_date:
                return ld_date

            date_el = soup.select_one("time.entry-date")
            if date_el:
                for candidate in (
                    date_el.get("datetime"),
                    date_el.get_text(strip=True),
                ):
                    if not candidate:
                        continue
                    text = candidate.strip()
                    if text[:1].isdigit():
                        return text
                    parsed = _parse_spanish_entry_date(text)
                    if parsed:
                        return parsed

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
        return result.metadata.get("title") or "Sin Título"

    def get_content(self, result: CrawlResult) -> str:
        soup = soup_from_result(result)
        if soup:
            content_el = soup.select_one("div.entry-content")
            if content_el:
                decompose_junk(
                    content_el,
                    (
                        "#gemini-summary-wrapper, #gemini-loading, "
                        "style, script, [data-beyondwords-player], "
                        ".sharedaddy, .jp-relatedposts"
                    ),
                )

                content = extract_blocks(
                    content_el,
                    "p",
                    junk_phrases=("Recibe en tu correo",),
                )
                if content:
                    return content
                return content_el.get_text("\n", strip=True)
        return result.markdown

    def is_valid_url(self, url: str) -> bool:
        if not url.startswith(self.base_url):
            return False

        parsed = urlparse(url)
        path = parsed.path.lower()
        if path in SECTION_INDEX_PATHS:
            return False
        if any(path.startswith(prefix) for prefix in NON_ARTICLE_PATH_PREFIXES):
            return False

        return bool(ARTICLE_PATH_PATTERN.fullmatch(path))
