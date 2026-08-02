import re

from common.sources import NewsSource
from ingestion.utils.c_detail import CDetailProvider, CDetailUrlMixin


class HoyProvider(CDetailUrlMixin, CDetailProvider):
    base_url = "https://hoy.com.do"
    source = NewsSource.HOY
    category_selectors = [
        "nav.c-detail__bar__category a",
        ".c-header--section__name a",
    ]
    content_junk_selectors = (
        ".c-detail__author, .c-detail__share, .c-detail__tags-content, "
        ".c-add, .c-add-600, .composite-video, .video-player, "
        ".c-detail__media, .c-detail__box, .c-author--detail, "
        ".Content_Bottom, .c-detail__info__more, "
        "style, script, iframe, aside, nav"
    )
    url_path_pattern = re.compile(r"/[^/]+/[^/]+_\d+\.html(?:\?|$)")
    url_denied_keywords = (
        "/autores/",
        "/autor/",
        "/tag/",
        "/tags/",
        "/page/",
        "/buscar",
        "/search",
        "/login",
        "/registro",
        "/suscrib",
        "/newsletter",
        "/obituarios/",
        "/galerias/",
        "/videos/",
        "/podcast",
        "/hoy-tv/",
        "/wp-content/",
        "/files/",
        "/contactos",
        "/quienes-somos",
        "/politicas-de-cookies",
        "/ediciones-impresas/",
        "/horoscopo/",
        "/loterias/",
    )
