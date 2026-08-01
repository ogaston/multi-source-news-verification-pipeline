"""Canonical news outlet names used across ingest, storage, and MCP."""

from __future__ import annotations

from enum import Enum


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
