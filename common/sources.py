"""Canonical news outlet names used across ingest, storage, and MCP."""

from __future__ import annotations

from enum import Enum


SOURCE_URLS: dict[str, str] = {
    "diario libre": "https://www.diariolibre.com",
    "listín diario": "https://listindiario.com",
    "listin diario": "https://listindiario.com",
    "hoy": "https://hoy.com.do",
    "acento": "https://acento.com.do",
    "el nuevo diario": "https://elnuevodiario.com.do",
    "somos pueblo": "https://somospueblo.com",
}


def source_url(name: str, default: str = "#") -> str:
    return SOURCE_URLS.get((name or "").casefold(), default)


class NewsSource(str, Enum):
    SOMOS_PUEBLO = "Somos Pueblo"
    EL_NUEVO_DIARIO = "El Nuevo Diario"
    LISTIN_DIARIO = "Listin Diario"
    DIARIO_LIBRE = "Diario Libre"
    HOY = "Hoy"
    ACENTO = "Acento"
    REMOLACHA = "Remolacha"
    EL_CARIBE = "El Caribe"
    EL_NACIONAL = "El Nacional"
    EL_DIA = "El Día"
