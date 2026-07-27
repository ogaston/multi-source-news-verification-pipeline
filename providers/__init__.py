from typing import Any

from providers.acento import AcentoProvider
from providers.diario_libre import DiarioLibreProvider
from providers.hoy import HoyProvider
from providers.listin_diario import ListinDiarioProvider
from providers.nuevo_diario import ElNuevoDiarioProvider
from providers.somos_pueblo import SomosPuebloProvider
from sources import NewsSource

NEWS_PROVIDERS: dict[NewsSource, Any] = {
    NewsSource.SOMOS_PUEBLO: SomosPuebloProvider,
    NewsSource.EL_NUEVO_DIARIO: ElNuevoDiarioProvider,
    NewsSource.LISTIN_DIARIO: ListinDiarioProvider,
    NewsSource.DIARIO_LIBRE: DiarioLibreProvider,
    NewsSource.HOY: HoyProvider,
    NewsSource.ACENTO: AcentoProvider,
}

__all__ = ["NEWS_PROVIDERS"]
