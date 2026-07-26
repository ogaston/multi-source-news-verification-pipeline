import re

from bs4 import BeautifulSoup
from crawl4ai.models import CrawlResult

from providers.base import BaseNewsProvider


class DiarioLibreProvider(BaseNewsProvider):
    base_url = "https://www.diariolibre.com"
    source = "Diario Libre"
    css_selector = "article"

    def get_author(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, "html.parser")
            author_el = soup.select_one('address.author a[rel="author"] strong')
            if author_el and author_el.get_text(strip=True):
                return author_el.get_text(strip=True)

            author_link = soup.select_one('address.author a[rel="author"]')
            if author_link and author_link.get_text(strip=True):
                return author_link.get_text(strip=True)

        for html in (result.html, result.cleaned_html):
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            meta_author = soup.select_one('meta[name="ArticleAuthors"]')
            if meta_author and meta_author.get("content"):
                return meta_author["content"].strip()

        return result.metadata.get("author") or "Sin Autor"

    def get_category(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, "html.parser")
            crumb = soup.select_one("ul.breadcrumb li:last-child")
            if crumb and crumb.get_text(strip=True):
                return crumb.get_text(strip=True)

            crumbs = soup.select("ul.breadcrumb li a[title]")
            if len(crumbs) >= 2 and crumbs[1].get_text(strip=True):
                return crumbs[1].get_text(strip=True)
            if crumbs and crumbs[0].get_text(strip=True):
                return crumbs[0].get_text(strip=True)

        for html in (result.html, result.cleaned_html):
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            meta_section = soup.select_one('meta[name="ArticleSubSectionURL"]')
            if meta_section and meta_section.get("content"):
                return meta_section["content"].strip().replace("-", " ").title()
            meta_section = soup.select_one('meta[name="ArticleSectionURL"]')
            if meta_section and meta_section.get("content"):
                return meta_section["content"].strip().replace("-", " ").title()

        return result.metadata.get("category") or "Sin Categoría"

    def get_date(self, result: CrawlResult) -> str:
        for html in (result.html, result.cleaned_html):
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            meta_date = soup.select_one('meta[name="ArticlePublicationDate"]')
            if meta_date and meta_date.get("content"):
                return meta_date["content"].strip()

            date_el = soup.select_one("time#detail-datetime, time[datetime]")
            if date_el:
                dt = (date_el.get("datetime") or "").strip()
                time_post = (date_el.get("time_post") or "").strip()
                if dt and time_post:
                    return f"{dt}T{time_post}"
                if dt:
                    return dt
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
            title_el = soup.select_one("article h1")
            if title_el:
                return title_el.get_text(strip=True)
        return result.metadata.get("title") or "Sin Título"

    def get_content(self, result: CrawlResult) -> str:
        html = result.cleaned_html or result.html
        if html:
            soup = BeautifulSoup(html, "html.parser")
            content_el = soup.select_one("div.detail-body")
            if content_el:
                for junk in content_el.select(
                    "#dynamic-resume, .trinity-skip-it, "
                    ".read-more, .tags-container, .author-info, "
                    ".share-icons, [id^=dl_], [id*=gpt-ad], "
                    "style, script, iframe, input, aside, nav"
                ):
                    junk.decompose()

                paragraphs = [
                    p.get_text(" ", strip=True)
                    for p in content_el.select("p")
                    if p.get_text(strip=True)
                    and "Recibe en tu correo" not in p.get_text()
                    and "Suscríbete" not in p.get_text()
                    and "Leer más" not in p.get_text()
                ]
                if paragraphs:
                    return "\n\n".join(paragraphs)

                return content_el.get_text("\n", strip=True)
        return result.markdown

    def is_valid_url(self, url: str) -> bool:
        if not url.startswith(self.base_url):
            return False

        if not re.search(r"/\d{4}/\d{2}/\d{2}/[^/]+/\d+(?:/)?(?:\?|$|#)", url):
            return False

        ignored_keywords = [
            "/autor/",
            "/tags/",
            "/tag/",
            "/page/",
            "/buscar",
            "/search",
            "/login",
            "/registro",
            "/suscrib",
            "/newsletters",
            "/podcasts/",
            "/podcast/",
            "/videos/",
            "/encuestas/",
            "/rss",
            "/contacto",
            "/aviso-legal",
            "/sobre-diario-libre",
            "/edicion-usa/",
            "/edicion-impresa/",
            "/archivo/",
            "/efemerides/",
            "/cumpleanos/",
            "/plaza-libre/",
            "/resultados-deportivos/",
            "/herramientas/",
        ]
        return not any(keyword in url for keyword in ignored_keywords)
