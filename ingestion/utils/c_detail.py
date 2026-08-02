"""Shared extraction logic for outlets using the c-detail article template."""

from __future__ import annotations

import re
from abc import ABC
from urllib.parse import urlparse

from crawl4ai.models import CrawlResult

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


class CDetailProvider(BaseNewsProvider, ABC):
    css_selector = "article.c-detail"
    content_body_selector = "div.c-detail__body"
    title_selector = "h1.c-detail__title"
    author_selector = "a.c-detail__author__name"
    category_selectors: list[str] = ["nav.c-detail__bar__category a"]
    date_meta_keys: list[str] = ["article:published_time"]
    date_selectors: list[str] = [
        "a.c-detail__info__more__date time[datetime]",
        "a.c-detail__info__more__date",
    ]
    content_junk_selectors = (
        ".c-detail__author, .c-detail__share, .c-detail__tags-content, "
        ".c-add, .c-add-600, .composite-video, .video-player, "
        ".c-detail__box, .c-author--detail, "
        "style, script, iframe, aside, nav"
    )
    content_junk_phrases: tuple[str, ...] = (
        "Recibe en tu correo",
        "Suscríbete",
        "Publicado por",
        "Creado:",
        "Actualizado:",
        "Sobre el autor",
        "googletag.cmd.push",
    )
    content_paragraph_selectors: list[str] = ["p.paragraph", "p"]
    content_direct_paragraphs = False
    use_json_ld_fallbacks = False

    def get_author(self, result: CrawlResult) -> str:
        soup = soup_from_result(result)
        if soup:
            author = first_text(soup, [self.author_selector])
            if author:
                return author

            if self.use_json_ld_fallbacks:
                ld_author = ld_field(news_article_ld(soup), "author")
                if ld_author:
                    return ld_author

        for soup in iter_html_variants(result):
            author = meta_content(soup, "article:author")
            if author:
                return author

        return result.metadata.get("author") or "Sin Autor"

    def get_category(self, result: CrawlResult) -> str:
        for soup in iter_html_variants(result, order=("cleaned_html", "html")):
            category = first_text(soup, self.category_selectors)
            if category:
                return category

            section = meta_content(soup, "article:section")
            if section:
                return section

            if self.use_json_ld_fallbacks:
                ld_section = ld_field(news_article_ld(soup), "articleSection")
                if ld_section:
                    return ld_section

        return result.metadata.get("category") or "Sin Categoría"

    def get_date(self, result: CrawlResult) -> str:
        for soup in iter_html_variants(result):
            for key in self.date_meta_keys:
                value = meta_content(soup, key)
                if value:
                    return value

            for selector in self.date_selectors:
                element = soup.select_one(selector)
                if not element:
                    continue
                if element.name == "time" and element.get("datetime"):
                    return element["datetime"].strip()
                text = element.get_text(" ", strip=True)
                if text:
                    return text

            if self.use_json_ld_fallbacks:
                published = ld_field(news_article_ld(soup), "datePublished")
                if published:
                    return published

        return (
            result.metadata.get("date")
            or result.metadata.get("og:article:published_time")
            or "Sin Fecha"
        )

    def get_title(self, result: CrawlResult) -> str:
        soup = soup_from_result(result)
        if soup:
            title = first_text(soup, [self.title_selector])
            if title:
                return title

            og_title = meta_content(soup, "og:title")
            if og_title:
                return og_title

            if self.use_json_ld_fallbacks:
                headline = ld_field(news_article_ld(soup), "headline")
                if headline:
                    return headline

        return result.metadata.get("title") or "Sin Título"

    def get_content(self, result: CrawlResult) -> str:
        soup = soup_from_result(result)
        if soup:
            content_el = soup.select_one(self.content_body_selector)
            if content_el:
                decompose_junk(content_el, self.content_junk_selectors)

                if self.content_direct_paragraphs:
                    content = extract_blocks(
                        content_el,
                        junk_phrases=self.content_junk_phrases,
                        direct_children=True,
                        paragraph_class="paragraph",
                    )
                else:
                    content = extract_blocks(
                        content_el,
                        self.content_paragraph_selectors,
                        junk_phrases=self.content_junk_phrases,
                        fallback_selectors=True,
                    )

                if content:
                    return content
                return content_el.get_text("\n", strip=True)

        return result.markdown


class CDetailUrlMixin:
    """URL validation helpers for c-detail outlets."""

    url_path_pattern: re.Pattern[str] | None = None
    url_denied_keywords: tuple[str, ...] = ()
    url_netloc: str | None = None
    url_require_https_startswith = True

    def is_valid_url(self, url: str) -> bool:
        if self.url_netloc:
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"}:
                return False
            if parsed.netloc != self.url_netloc:
                return False
            path = parsed.path.lower()
            if self.url_path_pattern and not self.url_path_pattern.fullmatch(path):
                return False
            return True

        if self.url_require_https_startswith and not url.startswith(self.base_url):
            return False

        if self.url_path_pattern and not self.url_path_pattern.search(url):
            return False

        return not any(keyword in url for keyword in self.url_denied_keywords)
