"""Seed a small published dataset for local demos and website CI."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import text

from common.db import get_engine

_SOURCES = json.dumps(
    [
        {"name": "Diario Libre", "url": "https://www.diariolibre.com"},
        {"name": "Listín Diario", "url": "https://listindiario.com"},
        {"name": "Acento", "url": "https://acento.com.do"},
    ],
    ensure_ascii=False,
)

_ARTICLES = (
    (
        "reforma-presupuesto",
        "Política",
        "El Congreso aprueba el nuevo presupuesto",
        "El Congreso aprobó el presupuesto tras varias semanas de negociación.\n\n"
        "La ley aumenta las partidas de salud y educación y reduce algunas "
        "inversiones de infraestructura. Distintos medios contrastaron el "
        "comunicado oficial con las cifras publicadas por Hacienda.",
        "alta",
    ),
    (
        "inflacion-datos",
        "Economía",
        "La inflación se modera por tercer mes consecutivo",
        "Los precios registraron una tercera lectura consecutiva a la baja.\n\n"
        "Los datos oficiales coinciden con la tendencia observada por organismos "
        "internacionales, aunque difieren ligeramente por metodología.",
        "alta",
    ),
    (
        "sequia-cuencas",
        "Clima",
        "Las reservas de agua caen a su nivel más bajo en una década",
        "Las principales cuencas registran reservas históricamente bajas.\n\n"
        "Autoridades y especialistas atribuyen el descenso a una combinación "
        "de menos lluvias y mayor demanda urbana y agrícola.",
        "en_revision",
    ),
    (
        "regulacion-ia",
        "Tecnología",
        "Entra en vigor el nuevo marco de inteligencia artificial",
        "La regulación clasifica los sistemas de inteligencia artificial por riesgo.\n\n"
        "Las aplicaciones de alto riesgo deberán documentar su entrenamiento, "
        "auditar sesgos y ofrecer canales de reclamación.",
        "alta",
    ),
    (
        "museo-restauracion",
        "Cultura",
        "Reabre el museo nacional tras cuatro años de restauración",
        "El museo nacional reabrió sus puertas después de cuatro años de obras.\n\n"
        "La primera fase recupera las salas permanentes y mejora la accesibilidad "
        "y la conservación de las colecciones.",
        "media",
    ),
    (
        "sanidad-lista-espera",
        "Sociedad",
        "Se reducen las listas de espera sanitarias",
        "Varias regiones reportaron una reducción de las listas de espera.\n\n"
        "Parte del cambio responde a horarios ampliados y a criterios estadísticos "
        "unificados, por lo que las comparaciones requieren cautela.",
        "media",
    ),
)


def seed() -> int:
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        {
            "id": f"demo-{index}",
            "cluster_id": f"demo-cluster-{index}",
            "slug": slug,
            "category": category,
            "title": title,
            "content": content,
            "confidence": confidence,
            "date": now,
            "created_at": now,
            "sources": _SOURCES,
        }
        for index, (slug, category, title, content, confidence) in enumerate(
            _ARTICLES, start=1
        )
    ]
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO verified_articles (
                    id, cluster_id, slug, title, content, category, date, sources,
                    status, confidence, created_at
                ) VALUES (
                    :id, :cluster_id, :slug, :title, :content, :category, :date,
                    :sources, 'published', :confidence, :created_at
                )
                ON CONFLICT (slug) DO UPDATE SET
                    title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    category = EXCLUDED.category,
                    date = EXCLUDED.date,
                    sources = EXCLUDED.sources,
                    confidence = EXCLUDED.confidence
                """
            ),
            rows,
        )
    return len(rows)


if __name__ == "__main__":
    print(f"Seeded {seed()} demo articles.")
