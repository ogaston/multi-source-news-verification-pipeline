"""Extraction and URL-filter tests for news providers."""

from types import SimpleNamespace

import pytest

from ingestion.pipeline import prepare_article
from ingestion.providers.el_caribe import ElCaribeProvider
from ingestion.providers.el_dia import ElDiaProvider
from ingestion.providers.el_nacional import ElNacionalProvider
from ingestion.providers.remolacha import RemolachaProvider


def crawl_result(html: str):
    return SimpleNamespace(
        cleaned_html=html,
        html=html,
        metadata={},
        markdown="markdown fallback",
    )


@pytest.mark.parametrize(
    ("provider_class", "valid_url", "invalid_urls"),
    [
        (
            RemolachaProvider,
            "https://remolacha.net/2026/07/alejandro-fernandez-dejara-el-cargo/",
            [
                "https://remolacha.net/category/noticias/",
                "https://remolacha.net/2026/07/slug/feed/",
                "https://example.com/2026/07/noticia/",
            ],
        ),
        (
            ElCaribeProvider,
            "https://www.elcaribe.com.do/panorama/pais/una-noticia/",
            [
                "https://www.elcaribe.com.do/seccion/panorama/",
                "https://www.elcaribe.com.do/autor/reportero/",
                "https://elcaribe.com.do/panorama/pais/una-noticia/",
            ],
        ),
        (
            ElNacionalProvider,
            "https://elnacional.com.do/nacionales/judicial/una-noticia_571390.html",
            [
                "https://elnacional.com.do/nacionales/",
                "https://elnacional.com.do/newsletter.html",
                "https://www.elnacional.com.do/economia/noticia_123.html",
            ],
        ),
        (
            ElDiaProvider,
            "https://eldia.com.do/alejandro-fernandez-renuncia-al-cargo/",
            [
                "https://eldia.com.do/secciones/nacionales/",
                "https://eldia.com.do/newsletter/",
                "https://eldia.com.do/contacto/",
            ],
        ),
    ],
)
def test_provider_url_filters(provider_class, valid_url, invalid_urls):
    provider = provider_class(None)
    assert provider.is_valid_url(valid_url)
    assert all(not provider.is_valid_url(url) for url in invalid_urls)


def test_remolacha_extracts_and_cleans_article():
    html = """
    <html><head>
      <meta property="article:published_time" content="2026-07-31T09:15:00-04:00">
    </head><body><div id="content">
      <div id="post-10" class="post type-post hentry category-noticias">
        <h1 class="post-title">Título Remolacha</h1>
        <div class="post-meta"><span class="author vcard">
          <span class="fn">Redacción Remolacha</span>
        </span></div>
        <div class="post-data"><a rel="category">* Noticias</a></div>
        <div class="post-entry">
          <p>Este es el contenido principal de la noticia con suficiente detalle.</p>
          <p>(Seguir leyendo…) texto que no pertenece al resumen.</p>
        </div>
      </div>
    </div></body></html>
    """
    provider = RemolachaProvider(None)
    result = crawl_result(html)

    article = provider.build_article(
        "https://remolacha.net/2026/07/titulo-remolacha/", result
    )
    prepared, reason = prepare_article(article)

    assert reason is None
    assert prepared is not None
    assert prepared["title"] == "Título Remolacha"
    assert prepared["author"] == "Redacción Remolacha"
    assert prepared["category"] == "Noticias"
    assert "Seguir leyendo" not in prepared["content"]


def test_remolacha_normalizes_spanish_dom_date():
    html = """
    <div id="content">
      <div id="post-11" class="post type-post hentry">
        <h1 class="post-title">Título con fecha visible</h1>
        <div class="post-meta">
          <a title="11:31 am"><span class="timestamp">Julio 31, 2026</span></a>
        </div>
      </div>
    </div>
    """
    provider = RemolachaProvider(None)

    assert provider.get_date(crawl_result(html)) == "2026-07-31T11:31:00-04:00"


def test_el_caribe_extracts_and_cleans_article():
    html = """
    <html><head>
      <meta property="article:published_time" content="2026-07-31T14:00:00Z">
    </head><body>
      <article class="type-post status-publish">
        <h1 class="entry-title">Título El Caribe</h1>
        <span class="author vcard"><a class="url fn n">Ana Pérez</a></span>
        <span class="cat-links"><a rel="category">País</a></span>
        <div class="entry-content"><div class="content">
          <p class="wp-block-paragraph">
            Este es el cuerpo principal de El Caribe con información verificable.
          </p>
          <div class="newsletter-block"><p>Recibe noticias en tu correo.</p></div>
        </div></div>
      </article>
    </body></html>
    """
    provider = ElCaribeProvider(None)
    result = crawl_result(html)

    article = provider.build_article(
        "https://www.elcaribe.com.do/panorama/pais/titulo-el-caribe/", result
    )
    prepared, reason = prepare_article(article)

    assert reason is None
    assert prepared is not None
    assert prepared["title"] == "Título El Caribe"
    assert prepared["author"] == "Ana Pérez"
    assert prepared["category"] == "País"
    assert "Recibe noticias" not in prepared["content"]


def test_el_nacional_extracts_only_direct_body_paragraphs():
    html = """
    <html><head>
      <meta property="article:published_time" content="2026-07-31T11:00:00-04:00">
    </head><body><article class="c-detail">
      <nav class="c-detail__bar__category"><a>Nacionales</a></nav>
      <h1 class="c-detail__title">Título El Nacional</h1>
      <a class="c-detail__author__name">Luis Gómez</a>
      <div class="c-detail__body">
        <p class="paragraph">
          Este es el texto directo y completo que pertenece a la noticia nacional.
        </p>
        <div class="related"><p class="paragraph">Contenido relacionado ajeno.</p></div>
      </div>
    </article></body></html>
    """
    provider = ElNacionalProvider(None)
    result = crawl_result(html)

    article = provider.build_article(
        "https://elnacional.com.do/nacionales/titulo_123.html", result
    )
    prepared, reason = prepare_article(article)

    assert reason is None
    assert prepared is not None
    assert prepared["title"] == "Título El Nacional"
    assert prepared["author"] == "Luis Gómez"
    assert prepared["category"] == "Nacionales"
    assert "Contenido relacionado" not in prepared["content"]


def test_el_dia_extracts_and_cleans_article():
    html = """
    <html><head>
      <meta property="article:published_time" content="2026-07-31T08:30:00-04:00">
    </head><body><main id="main-content"><section class="single">
      <h1 class="single-title">Título El Día</h1>
      <div class="author-short">
        <a rel="author">María Díaz</a>
        <a href="/secciones/nacionales/">Nacionales</a>
      </div>
      <div class="content pt-3 border-top">
        <p>Este es el contenido principal de El Día con suficiente información.</p>
        <div class="puede-leer-module"><p>Puede leer otra noticia.</p></div>
      </div>
    </section></main></body></html>
    """
    provider = ElDiaProvider(None)
    result = crawl_result(html)

    article = provider.build_article(
        "https://eldia.com.do/titulo-de-la-noticia/", result
    )
    prepared, reason = prepare_article(article)

    assert reason is None
    assert prepared is not None
    assert prepared["title"] == "Título El Día"
    assert prepared["author"] == "María Díaz"
    assert prepared["category"] == "Nacionales"
    assert "Puede leer" not in prepared["content"]
