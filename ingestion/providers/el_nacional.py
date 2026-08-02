import re

from common.sources import NewsSource
from ingestion.utils.c_detail import CDetailProvider, CDetailUrlMixin


class ElNacionalProvider(CDetailUrlMixin, CDetailProvider):
    base_url = "https://elnacional.com.do"
    source = NewsSource.EL_NACIONAL
    use_json_ld_fallbacks = True
    content_junk_selectors = (
        ".c-detail__author, .c-detail__tags-content, .c-add, "
        ".c-add-600, .composite-video, .video-player, "
        ".c-detail__box, .c-detail__share, .c-author--detail, "
        "script, style, iframe, aside, nav"
    )
    content_direct_paragraphs = True
    url_netloc = "elnacional.com.do"
    url_path_pattern = re.compile(r"/(?:[^/]+/){1,2}[^/]+_\d+\.html")
