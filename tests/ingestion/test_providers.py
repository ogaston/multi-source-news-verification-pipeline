"""Extraction and URL-filter tests for news providers."""

from types import SimpleNamespace

import pytest

from ingestion.pipeline import prepare_article
from ingestion.providers.acento import AcentoProvider
from ingestion.providers.diario_libre import DiarioLibreProvider
from ingestion.providers.el_caribe import ElCaribeProvider
from ingestion.providers.el_dia import ElDiaProvider
from ingestion.providers.el_nacional import ElNacionalProvider
from ingestion.providers.hoy import HoyProvider
from ingestion.providers.listin_diario import ListinDiarioProvider
from ingestion.providers.nuevo_diario import ElNuevoDiarioProvider
from ingestion.providers.remolacha import RemolachaProvider
from ingestion.providers.somos_pueblo import SomosPuebloProvider


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
        (
            AcentoProvider,
            "https://acento.com.do/actualidad/noticia-de-prueba-123456.html",
            [
                "https://acento.com.do/seccion/actualidad/",
                "https://example.com/actualidad/noticia-de-prueba-123456.html",
            ],
        ),
        (
            DiarioLibreProvider,
            "https://www.diariolibre.com/actualidad/nacional/2026/08/01/noticia/1234567",
            [
                "https://www.diariolibre.com/actualidad/nacional/",
                "https://www.diariolibre.com/autor/reportero/2026/08/01/noticia/1234567",
            ],
        ),
        (
            HoyProvider,
            "https://hoy.com.do/el-pais/noticia-de-prueba_123456.html",
            [
                "https://hoy.com.do/el-pais/",
                "https://hoy.com.do/videos/noticia-de-prueba_123456.html",
            ],
        ),
        (
            ListinDiarioProvider,
            "https://listindiario.com/la-republica/20260801/noticia-de-prueba_123456.html",
            [
                "https://listindiario.com/la-republica/",
                "https://listindiario.com/videos/20260801/noticia-de-prueba_123456.html",
            ],
        ),
        (
            ElNuevoDiarioProvider,
            "https://elnuevodiario.com.do/gobierno-anuncia-medida/",
            [
                "https://elnuevodiario.com.do/nacionales/",
                "https://example.com/gobierno-anuncia-medida/",
            ],
        ),
        (
            SomosPuebloProvider,
            "https://somospueblo.com/gobierno-anuncia-medida/",
            [
                "https://somospueblo.com/actualidad/",
                "https://example.com/gobierno-anuncia-medida/",
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


def assert_extracted_fields(provider_class, url, html, expected):
    article = provider_class(None).build_article(url, crawl_result(html))

    assert {
        field: article[field]
        for field in ("title", "author", "category", "date", "content")
    } == expected


def test_acento_extracts_article_fields():
    html = """
    <article id="mainArticle">
      <h1>Título Acento</h1>
      <div class="breadcrumbs"><span class="section-name"><a>Actualidad</a></span></div>
      <div class="autor"><span class="name"><a>Ana Acento</a></span></div>
      <amp-timeago datetime="2026-08-01T09:00:00-04:00"></amp-timeago>
      <div class="article-body">
        <p>Contenido principal de Acento para comprobar la extracción sin usar la red.</p>
      </div>
    </article>
    """

    assert_extracted_fields(
        AcentoProvider,
        "https://acento.com.do/actualidad/noticia-de-prueba-123456.html",
        html,
        {
            "title": "Título Acento",
            "author": "Ana Acento",
            "category": "Actualidad",
            "date": "2026-08-01T09:00:00-04:00",
            "content": (
                "Contenido principal de Acento para comprobar la extracción sin usar la red."
            ),
        },
    )


def test_diario_libre_extracts_article_fields():
    html = """
    <html><head>
      <meta name="ArticlePublicationDate" content="2026-08-01T10:00:00-04:00">
    </head><body><article>
      <h1>Título Diario Libre</h1>
      <address class="author"><a rel="author"><strong>Diego Libre</strong></a></address>
      <ul class="breadcrumb"><li>Inicio</li><li>Nacional</li></ul>
      <div class="detail-body">
        <p>Contenido principal de Diario Libre extraído desde una fixture local.</p>
      </div>
    </article></body></html>
    """

    assert_extracted_fields(
        DiarioLibreProvider,
        "https://www.diariolibre.com/actualidad/nacional/2026/08/01/noticia/1234567",
        html,
        {
            "title": "Título Diario Libre",
            "author": "Diego Libre",
            "category": "Nacional",
            "date": "2026-08-01T10:00:00-04:00",
            "content": "Contenido principal de Diario Libre extraído desde una fixture local.",
        },
    )


def test_hoy_extracts_article_fields():
    html = """
    <html><head>
      <meta property="article:published_time" content="2026-08-01T11:00:00-04:00">
    </head><body><article class="c-detail">
      <h1 class="c-detail__title">Título Hoy</h1>
      <a class="c-detail__author__name">Helena Hoy</a>
      <nav class="c-detail__bar__category"><a>El País</a></nav>
      <div class="c-detail__body">
        <p class="paragraph">Contenido principal de Hoy extraído desde una fixture local.</p>
      </div>
    </article></body></html>
    """

    assert_extracted_fields(
        HoyProvider,
        "https://hoy.com.do/el-pais/noticia-de-prueba_123456.html",
        html,
        {
            "title": "Título Hoy",
            "author": "Helena Hoy",
            "category": "El País",
            "date": "2026-08-01T11:00:00-04:00",
            "content": "Contenido principal de Hoy extraído desde una fixture local.",
        },
    )


def test_listin_diario_extracts_article_fields():
    html = """
    <html><head>
      <meta property="article:published_time" content="2026-08-01T12:00:00-04:00">
    </head><body><article class="c-detail">
      <h1 class="c-detail__title">Título Listín Diario</h1>
      <span class="c-detail__author__name">Laura Listín</span>
      <div class="c-menu-section"><a>La República</a></div>
      <div class="c-detail__body">
        <p>Contenido principal de Listín Diario extraído desde una fixture local.</p>
      </div>
    </article></body></html>
    """

    assert_extracted_fields(
        ListinDiarioProvider,
        "https://listindiario.com/la-republica/20260801/noticia-de-prueba_123456.html",
        html,
        {
            "title": "Título Listín Diario",
            "author": "Laura Listín",
            "category": "La República",
            "date": "2026-08-01T12:00:00-04:00",
            "content": "Contenido principal de Listín Diario extraído desde una fixture local.",
        },
    )


def test_nuevo_diario_extracts_article_fields():
    html = """
    <html><head>
      <meta property="article:published_time" content="2026-08-01T13:00:00-04:00">
    </head><body><article class="noticia-detalle">
      <header class="entry-header">
        <h1 class="entry-title">Título El Nuevo Diario</h1>
        <div class="entry-meta"><a href="/author/elena/"><b>Elena Diario</b></a></div>
      </header>
      <a class="section-name">Nacionales</a>
      <div class="entry-content">
        <p>Contenido principal de El Nuevo Diario extraído desde una fixture local.</p>
      </div>
    </article></body></html>
    """

    assert_extracted_fields(
        ElNuevoDiarioProvider,
        "https://elnuevodiario.com.do/gobierno-anuncia-medida/",
        html,
        {
            "title": "Título El Nuevo Diario",
            "author": "Elena Diario",
            "category": "Nacionales",
            "date": "2026-08-01T13:00:00-04:00",
            "content": (
                "Contenido principal de El Nuevo Diario extraído desde una fixture local."
            ),
        },
    )


def test_nuevo_diario_parses_spanish_entry_date():
    """Live site puts Spanish prose in time.datetime and omits article:published_time."""
    html = """
    <article class="noticia-detalle">
      <h1 class="entry-title">Sismo de magnitud 4.73</h1>
      <time class="entry-date published" datetime="sábado, 1 de agosto 2026 | 8:59 am">
        sábado, 1 de agosto 2026 | 8:59 am
      </time>
      <div class="entry-content">
        <p>Contenido principal de El Nuevo Diario con fecha en español.</p>
      </div>
    </article>
    """
    provider = ElNuevoDiarioProvider(None)
    article = provider.build_article(
        "https://elnuevodiario.com.do/sismo-de-magnitud-4-73/",
        crawl_result(html),
    )
    prepared, reason = prepare_article(article)

    assert provider.get_date(crawl_result(html)) == "2026-08-01T08:59:00-04:00"
    assert reason is None
    assert prepared is not None
    assert prepared["date"] == "2026-08-01T12:59:00Z"


def test_somos_pueblo_extracts_article_fields():
    html = """
    <div class="wpb_wrapper">
      <h1 class="tdb-title-text">Título Somos Pueblo</h1>
      <a class="tdb-author-name">Sara Pueblo</a>
      <a class="tdb-entry-category">Política</a>
      <time class="entry-date" datetime="2026-08-01T14:00:00-04:00"></time>
      <div class="tdb_single_content">
        <p>Contenido principal de Somos Pueblo extraído desde una fixture local.</p>
      </div>
    </div>
    """

    assert_extracted_fields(
        SomosPuebloProvider,
        "https://somospueblo.com/gobierno-anuncia-medida/",
        html,
        {
            "title": "Título Somos Pueblo",
            "author": "Sara Pueblo",
            "category": "Política",
            "date": "2026-08-01T14:00:00-04:00",
            "content": "Contenido principal de Somos Pueblo extraído desde una fixture local.",
        },
    )


def test_somos_pueblo_reads_fields_from_article_scoped_html():
    """crawl4ai css_selector=article still includes title outside the content block."""
    article_html = """
    <article>
      <h1 class="tdb-title-text">Intiman a la Cámara de Cuentas</h1>
      <a class="tdb-author-name">Redacción SP</a>
      <a class="tdb-entry-category">Nacional</a>
      <time class="entry-date" datetime="2026-08-02T10:00:00-04:00"></time>
      <div class="tdb_single_content">
        <p>Cuerpo de la nota con suficiente texto para el extractor.</p>
      </div>
    </article>
    """
    # Mimic crawl4ai: both html and cleaned_html are selector-scoped; metadata empty.
    result = SimpleNamespace(
        cleaned_html=article_html,
        html=article_html,
        metadata={},
        markdown="markdown fallback",
    )
    article = SomosPuebloProvider(None).build_article(
        "https://somospueblo.com/intiman-a-la-camara-de-cuentas/",
        result,
    )

    assert article["title"] == "Intiman a la Cámara de Cuentas"
    assert article["author"] == "Redacción SP"
    assert article["category"] == "Nacional"
    assert article["date"] == "2026-08-02T10:00:00-04:00"
    assert "Cuerpo de la nota" in article["content"]
