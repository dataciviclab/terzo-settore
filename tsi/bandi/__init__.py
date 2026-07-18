"""Catalogo fonti bandi — adapter, registry, deduplica.

Uso:
    from tsi.bandi.registry import Registry
    from tsi.bandi.fonti.infobandi import InfobandiAdapter
    from tsi.bandi.dedup import deduplica

    registry = Registry()
    registry.carica("infobandi", InfobandiAdapter)
    bandi = registry.fetch_tutti()
    bandi_unici = deduplica(bandi)
"""

from tsi.bandi.base import BandoNormalizzato, FonteBandi
from tsi.bandi.registry import Registry
from tsi.bandi.dedup import deduplica

__all__ = ["BandoNormalizzato", "FonteBandi", "Registry", "deduplica"]
