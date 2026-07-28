from typing import Any

from common.sources import NewsSource
from ingestion.providers.acento import AcentoProvider
from ingestion.providers.diario_libre import DiarioLibreProvider
from ingestion.providers.hoy import HoyProvider
from ingestion.providers.listin_diario import ListinDiarioProvider
from ingestion.providers.nuevo_diario import ElNuevoDiarioProvider
from ingestion.providers.somos_pueblo import SomosPuebloProvider

NEWS_PROVIDERS: dict[NewsSource, Any] = {
    NewsSource.SOMOS_PUEBLO: SomosPuebloProvider,
    NewsSource.EL_NUEVO_DIARIO: ElNuevoDiarioProvider,
    NewsSource.LISTIN_DIARIO: ListinDiarioProvider,
    NewsSource.DIARIO_LIBRE: DiarioLibreProvider,
    NewsSource.HOY: HoyProvider,
    NewsSource.ACENTO: AcentoProvider,
}

__all__ = ["NEWS_PROVIDERS"]
