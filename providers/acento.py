import json
import re

from bs4 import BeautifulSoup
from crawl4ai.models import CrawlResult

from providers.base import BaseNewsProvider
from sources import NewsSource


class AcentoProvider(BaseNewsProvider):
    base_url = "https://acento.com.do"
    source = NewsSource.ACENTO
    css_selector = "article#mainArticle"

    def get_author(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, "html.parser")
            author_el = soup.select_one("div.autor span.name a")
            if author_el and author_el.get_text(strip=True):
                return author_el.get_text(strip=True)

            author_el = soup.select_one("div.autor span.name")
            if author_el and author_el.get_text(strip=True):
                return author_el.get_text(strip=True)

        return result.metadata.get("author") or "Sin Autor"

    def get_category(self, result: CrawlResult) -> str:
        for html in (result.cleaned_html, result.html):
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            category_el = soup.select_one(
                ".breadcrumbs span.section-name a, span.section-name a"
            )
            if category_el and category_el.get_text(strip=True):
                return category_el.get_text(strip=True)

            for script in soup.select('script[type="application/ld+json"]'):
                try:
                    data = json.loads(script.string or script.get_text() or "")
                except json.JSONDecodeError:
                    continue
                if isinstance(data, dict) and data.get("articleSection"):
                    return str(data["articleSection"]).strip()

        return result.metadata.get("category") or "Sin Categoría"

    def get_date(self, result: CrawlResult) -> str:
        for html in (result.html, result.cleaned_html):
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")

            time_el = soup.select_one("amp-timeago[datetime]")
            if time_el and time_el.get("datetime"):
                return time_el["datetime"].strip()

            for script in soup.select('script[type="application/ld+json"]'):
                try:
                    data = json.loads(script.string or script.get_text() or "")
                except json.JSONDecodeError:
                    continue
                if isinstance(data, dict) and data.get("datePublished"):
                    return str(data["datePublished"]).strip()

            meta_date = soup.select_one('meta[property="article:published_time"]')
            if meta_date and meta_date.get("content"):
                return meta_date["content"].strip()

        return (
            result.metadata.get("date")
            or result.metadata.get("og:article:published_time")
            or "Sin Fecha"
        )

    def get_title(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, "html.parser")
            title_el = soup.select_one("article#mainArticle h1")
            if title_el:
                return title_el.get_text(strip=True)
        return result.metadata.get("title") or "Sin Título"

    def get_content(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, "html.parser")
            content_el = soup.select_one("div.article-body")
            if content_el:
                for junk in content_el.select(
                    "#newsletter, .banner-box, .related-news, "
                    ".nota-bottom-author, .nota-bottom-share, "
                    ".bottom-follow-btns, .con-tags-container, "
                    "script, style, amp-ad, iframe"
                ):
                    junk.decompose()

                junk_phrases = (
                    "Recibe en tu correo",
                    "¡No te pierdas",
                    "Compartir esta nota",
                    "Sigue todas las noticias",
                    "Sigue  todas las noticias",
                    "MIRA TAMBIÉN",
                )
                blocks = []
                for el in content_el.select("p, h2, h3, li"):
                    text = el.get_text(" ", strip=True)
                    if not text:
                        continue
                    if any(phrase in text for phrase in junk_phrases):
                        continue
                    blocks.append(text)

                if blocks:
                    return "\n\n".join(blocks)

                return content_el.get_text("\n", strip=True)
        return result.markdown

    def is_valid_url(self, url: str) -> bool:
        if not url.startswith(self.base_url):
            return False

        ignored_keywords = [
            "/seccion/",
            "/autor/",
            "/tags/",
            "/buscar/",
            "/ultimas-noticias",
            "/resources/",
            "/media/",
            "/page/",
            "/wp-content/",
            "/wp-admin/",
            "/en-vivo",
            "/podcast/",
            "/videos/",
            "/contacto",
            "/quienes-somos",
            "/politica-de-privacidad",
            "/terminos",
            "/newsletter",
            "/amp/",
        ]
        if any(keyword in url for keyword in ignored_keywords):
            return False

        return bool(re.search(r"/[^/]+/.+-\d+\.html(?:\?.*)?$", url))
