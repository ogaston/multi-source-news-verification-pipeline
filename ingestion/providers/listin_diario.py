import re

from common.sources import NewsSource
from ingestion.utils.c_detail import CDetailProvider, CDetailUrlMixin


class ListinDiarioProvider(CDetailUrlMixin, CDetailProvider):
    base_url = "https://listindiario.com"
    source = NewsSource.LISTIN_DIARIO
    author_selector = "span.c-detail__author__name"
    category_selectors = [".c-menu-section a"]
    date_selectors = ["time.c-detail__date"]
    content_junk_selectors = (
        ".c-add, .c-detail__share, .c-detail__tags, "
        ".c-detail__comments, .c-detail__tepuedeinteresar, "
        ".c-detail__mostread, .c-detail__bio, "
        "style, script, iframe, aside, nav"
    )
    content_paragraph_selectors = ["p"]
    url_path_pattern = re.compile(r"/\d{8}/[^/]+_\d+\.html(?:\?|$)")
    url_denied_keywords = (
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
    )
