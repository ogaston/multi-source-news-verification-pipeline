"""Fixture articles ported from the former website mock data."""

from __future__ import annotations

from api.schemas import Article, ArticleSource

_diario_libre = ArticleSource(name="Diario Libre", url="https://www.diariolibre.com")
_listin_diario = ArticleSource(name="Listín Diario", url="https://listindiario.com")
_hoy = ArticleSource(name="Hoy", url="https://hoy.com.do")
_acento = ArticleSource(name="Acento", url="https://acento.com.do")
_nuevo_diario = ArticleSource(
    name="El Nuevo Diario", url="https://elnuevodiario.com.do"
)
_somos_pueblo = ArticleSource(name="Somos Pueblo", url="https://somospueblo.com")

MOCK_ARTICLES: list[Article] = [
    Article(
        slug="reforma-presupuesto",
        category="Política",
        title=(
            "El Congreso aprueba el nuevo presupuesto tras semanas de negociación"
        ),
        summary=(
            "La ley destina más fondos a sanidad y educación, mientras recorta "
            "partidas de infraestructura. Recogemos los argumentos de las "
            "principales fuerzas políticas y el análisis de economistas "
            "independientes, sin adjetivos ni titulares alarmistas."
        ),
        body=[
            (
                "Tras varias semanas de negociación entre bancadas, el Congreso "
                "aprobó el proyecto de presupuesto para el próximo ejercicio "
                "fiscal. El texto final eleva las partidas de sanidad y educación "
                "y reduce inversiones previstas en obras de infraestructura."
            ),
            (
                "El Ejecutivo presentó la reforma como un reordenamiento del "
                "gasto hacia prioridades sociales. La oposición sostuvo que los "
                "recortes en obra pública pueden afectar el empleo en el sector "
                "de la construcción y ralentizar proyectos ya adjudicados."
            ),
            (
                "Economistas consultados por distintas redacciones coinciden en "
                "que el impacto fiscal agregado sería moderado: el déficit "
                "proyectado apenas varía respecto al escenario base, aunque la "
                "composición del gasto cambia de forma apreciable."
            ),
            (
                "Varios medios contrastaron el comunicado oficial con las cifras "
                "del Ministerio de Hacienda y con proyecciones de organismos "
                "independientes. Las diferencias se concentran en el calendario "
                "de ejecución, no en el monto total autorizado."
            ),
            (
                "La norma entra en vigor el 1 de enero. Los ministerios "
                "afectados deberán presentar planes de ajuste en un plazo de "
                "60 días."
            ),
        ],
        image="/images/lead-congress.png",
        imageAlt="Hemiciclo del Congreso durante la sesión de votación del presupuesto",
        imageCaption="Imagen ilustrativa · Redacción Ojo Crítico",
        readTime="6 min",
        confidence="alta",
        sources=[
            _diario_libre,
            _listin_diario,
            _hoy,
            _acento,
            _nuevo_diario,
            _somos_pueblo,
        ],
        date="30 de julio de 2026",
        perspectives=[
            "Gobierno: prioriza el gasto social",
            "Oposición: advierte del impacto en el empleo",
            "Analistas: efecto fiscal moderado",
        ],
    ),
    Article(
        slug="inflacion-datos",
        category="Economía",
        title="La inflación se modera por tercer mes consecutivo",
        summary=(
            "Los precios suben un 2,4% interanual. Contrastamos los datos "
            "oficiales con los de organismos internacionales para ofrecer una "
            "lectura completa."
        ),
        body=[
            (
                "El índice de precios al consumidor registró una variación "
                "interanual del 2,4%, la tercera lectura consecutiva a la baja. "
                "El descenso se explica, en buena parte, por la estabilización "
                "de los precios de los alimentos y la energía."
            ),
            (
                "Las cifras oficiales coinciden en la dirección del movimiento "
                "con las estimaciones de organismos internacionales, aunque "
                "difieren en unas décimas según la cesta de productos utilizada."
            ),
            (
                "Analistas de mercado subrayan que la inflación subyacente "
                "—sin energía ni alimentos frescos— se mantiene algo por encima, "
                "lo que sugiere que la presión de precios no ha desaparecido "
                "del todo."
            ),
            (
                "El banco central no anunció cambios inmediatos en su política "
                "monetaria. En rueda de prensa, indicó que seguirá evaluando "
                "los datos mes a mes."
            ),
        ],
        image="/images/economy.png",
        imageAlt="Gráfico y billetes sobre una mesa de trabajo económico",
        imageCaption="Imagen ilustrativa · Redacción Ojo Crítico",
        readTime="4 min",
        confidence="alta",
        sources=[
            _diario_libre,
            _listin_diario,
            _hoy,
            _acento,
            _nuevo_diario,
            _somos_pueblo,
        ],
        date="30 de julio de 2026",
    ),
    Article(
        slug="sequia-cuencas",
        category="Clima",
        title="Las reservas de agua caen a su nivel más bajo en una década",
        summary=(
            "Expertos y autoridades locales difieren sobre las causas. "
            "Presentamos ambas posturas junto a los datos hidrológicos "
            "disponibles."
        ),
        body=[
            (
                "Las reservas embalsadas en las principales cuencas se sitúan "
                "en su nivel más bajo de los últimos diez años, según los "
                "últimos boletines hidrológicos."
            ),
            (
                "Las autoridades locales atribuyen el descenso a un período de "
                "lluvias inferior a la media. Varios expertos independientes "
                "señalan, además, el aumento de la demanda urbana y agrícola."
            ),
            (
                "Los datos disponibles muestran que la ocupación de los "
                "embalses ha caído de forma sostenida desde hace tres campañas, "
                "con un ritmo más acusado en las cuencas del interior."
            ),
            (
                "Se han anunciado restricciones temporales en el riego de "
                "determinadas zonas. El abastecimiento doméstico, de momento, "
                "no está sujeto a cortes programados."
            ),
        ],
        image="/images/climate.png",
        imageAlt="Embalse con nivel de agua notablemente bajo",
        imageCaption="Imagen ilustrativa · Redacción Ojo Crítico",
        readTime="5 min",
        confidence="en_revision",
        sources=[
            _listin_diario,
            _hoy,
            _acento,
            _nuevo_diario,
            _somos_pueblo,
            _diario_libre,
        ],
        date="29 de julio de 2026",
    ),
    Article(
        slug="regulacion-ia",
        category="Tecnología",
        title=(
            "El nuevo marco de regulación de la inteligencia artificial "
            "entra en vigor"
        ),
        summary=(
            "Qué cambia para empresas y usuarios, explicado sin tecnicismos "
            "ni exageraciones."
        ),
        body=[
            (
                "El nuevo marco normativo sobre inteligencia artificial entra "
                "en vigor tras un período de transición de dieciocho meses. "
                "Clasifica los sistemas según su nivel de riesgo y fija "
                "obligaciones distintas para cada categoría."
            ),
            (
                "Las empresas que operen sistemas de alto riesgo deberán "
                "documentar el entrenamiento, auditar sesgos y ofrecer "
                "canales de reclamación. Los usos de riesgo limitado tendrán "
                "requisitos de transparencia más ligeros."
            ),
            (
                "Para los usuarios, el cambio más visible será la obligación "
                "de identificar contenidos generados automáticamente en "
                "contextos comerciales y electorales."
            ),
            (
                "Asociaciones empresariales han pedido guías prácticas antes "
                "de las primeras inspecciones. Las autoridades reguladoras "
                "anunciaron un calendario de consultas públicas."
            ),
        ],
        image="/images/technology.png",
        imageAlt="Circuito y código asociados a sistemas de inteligencia artificial",
        imageCaption="Imagen ilustrativa · Redacción Ojo Crítico",
        readTime="5 min",
        confidence="alta",
        sources=[
            _diario_libre,
            _listin_diario,
            _hoy,
            _acento,
            _nuevo_diario,
            _somos_pueblo,
        ],
        date="29 de julio de 2026",
    ),
    Article(
        slug="museo-restauracion",
        category="Cultura",
        title="Reabre el museo nacional tras cuatro años de restauración",
        summary=(
            "Un recorrido por las obras recuperadas y el debate sobre la "
            "financiación pública de la cultura."
        ),
        body=[
            (
                "El museo nacional reabre sus puertas tras cuatro años de obras "
                "de restauración estructural y de conservación de colecciones. "
                "La primera fase incluye las salas permanentes de pintura y "
                "escultura."
            ),
            (
                "El coste total del proyecto ha reabierto el debate sobre la "
                "financiación pública de la cultura. El ministerio defiende "
                "la inversión como patrimonio; críticos piden mayor "
                "transparencia en las adjudicaciones."
            ),
            (
                "Visitantes y guías destacan la mejora en iluminación y "
                "accesibilidad. Algunas piezas siguen en reserva a la espera "
                "de la segunda fase, prevista para el próximo año."
            ),
        ],
        image="/images/culture.png",
        imageAlt="Sala de museo con obras restauradas bajo nueva iluminación",
        imageCaption="Imagen ilustrativa · Redacción Ojo Crítico",
        readTime="3 min",
        confidence="media",
        sources=[_diario_libre, _listin_diario, _hoy],
        date="28 de julio de 2026",
    ),
    Article(
        slug="sanidad-lista-espera",
        category="Sociedad",
        title="Las listas de espera sanitarias se reducen en seis comunidades",
        summary=(
            "Comparamos las cifras entre regiones y explicamos la "
            "metodología detrás de cada estadística."
        ),
        body=[
            (
                "Seis comunidades autónomas reportan una reducción en las "
                "listas de espera quirúrgica respecto al mismo trimestre del "
                "año anterior. El descenso medio ronda el 8%, con diferencias "
                "notables entre regiones."
            ),
            (
                "Parte de la variación se explica por cambios metodológicos: "
                "algunas administraciones han unificado criterios de inclusión "
                "que antes diferían. Otras han ampliado horarios de quirófano."
            ),
            (
                "Organizaciones de pacientes advierten de que la mejora no es "
                "homogénea en todas las especialidades. Traumatología y "
                "oftalmología concentran aún los mayores retrasos."
            ),
        ],
        readTime="4 min",
        confidence="media",
        sources=[_listin_diario, _hoy, _acento],
        date="28 de julio de 2026",
    ),
    Article(
        slug="transporte-electrico",
        category="Movilidad",
        title="El transporte público eléctrico se duplica en las grandes ciudades",
        summary=(
            "Ventajas, costes y críticas de un plan que divide a expertos "
            "en movilidad urbana."
        ),
        body=[
            (
                "La flota de autobuses eléctricos en las grandes ciudades se "
                "ha duplicado en dos años, según datos de los operadores "
                "municipales. El despliegue incluye también nuevas líneas de "
                "tranvía en tres áreas metropolitanas."
            ),
            (
                "Los defensores del plan destacan la reducción de emisiones "
                "locales y del ruido. Los críticos apuntan al coste de las "
                "baterías, la dependencia de la red eléctrica y los plazos "
                "de amortización."
            ),
            (
                "Expertos en movilidad urbana coinciden en que el impacto "
                "depende de la generación eléctrica de respaldo y de la "
                "integración con otros modos de transporte, no solo del "
                "cambio de motor."
            ),
        ],
        readTime="4 min",
        confidence="baja",
        sources=[_diario_libre],
        date="27 de julio de 2026",
    ),
]


def list_mock_articles() -> list[Article]:
    return list(MOCK_ARTICLES)


def get_mock_article(slug: str) -> Article | None:
    for article in MOCK_ARTICLES:
        if article.slug == slug:
            return article
    return None
