"""Deduplica cross-fonte per hash del contenuto.

Stesso bando pubblicato da Infobandi e Info-cooperazione?
Il sistema tiene il record con più campi compilati.
"""

from tsi.bandi.base import BandoNormalizzato
import logging

logger = logging.getLogger(__name__)


def deduplica(bandi: list[BandoNormalizzato]) -> list[BandoNormalizzato]:
    """Unisce bandi da più fonti, tenendo il più ricco in caso di duplicato.

    Criterio di merge:
    - hash_contenuto identico → stesso bando
    - tiene quello con più campi compilati (budget, scadenza, descrizione)
    - a parità di campi, tiene il primo in ordine di arrivo
    """
    visti: dict[str, BandoNormalizzato] = {}
    for b in bandi:
        if not b.valido:
            logger.warning(f"Bando non valido scartato: {b.titolo[:50]} da {b.fonte}")
            continue

        if b.hash_contenuto in visti:
            esistente = visti[b.hash_contenuto]
            if _campi_compilati(b) > _campi_compilati(esistente):
                logger.debug(
                    f"Deduplica: {b.titolo[:40]} — merge {b.fonte} > {esistente.fonte}"
                )
                visti[b.hash_contenuto] = b
        else:
            visti[b.hash_contenuto] = b

    return list(visti.values())


def _campi_compilati(b: BandoNormalizzato) -> int:
    """Quanti campi opzionali sono compilati (0-3)."""
    return sum([
        1 if b.budget is not None else 0,
        1 if b.scadenza is not None else 0,
        1 if b.descrizione else 0,
    ])
