from typing import Any

from providers.acento import AcentoProvider
from providers.diario_libre import DiarioLibreProvider
from providers.hoy import HoyProvider
from providers.listin_diario import ListinDiarioProvider
from providers.nuevo_diario import ElNuevoDiarioProvider
from providers.somos_pueblo import SomosPuebloProvider

NEWS_PROVIDERS: dict[str, Any] = {
    "Somos Pueblo": SomosPuebloProvider,
    "El Nuevo Diario": ElNuevoDiarioProvider,
    "Listin Diario": ListinDiarioProvider,
    "Diario Libre": DiarioLibreProvider,
    "Hoy": HoyProvider,
    "Acento": AcentoProvider,
}

__all__ = ["NEWS_PROVIDERS"]
