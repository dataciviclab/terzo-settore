"""Test Registry: carica, fetch, healthcheck."""

from tsi.bandi.registry import Registry
from tsi.bandi.fonti.infobandi import InfobandiAdapter


class TestRegistry:
    def test_carica_e_lista(self):
        """Registra una fonte e la ritorna nella lista."""
        registry = Registry()
        registry.carica("infobandi", InfobandiAdapter)
        fonti = registry.lista()
        assert "infobandi" in fonti

    def test_carica_disabilitata(self):
        """Fonte disabilitata non viene fetchata."""
        registry = Registry()
        registry.carica("infobandi", InfobandiAdapter, stato="disabilitato")
        bandi = registry.fetch("infobandi")
        assert bandi == [], "Fonti disabilitate non devono produrre bandi"

    def test_fetch_fonte_inesistente(self):
        """Fonte non registrata ritorna lista vuota."""
        registry = Registry()
        bandi = registry.fetch("non-esiste")
        assert bandi == []

    def test_healthcheck_ritorna_report(self):
        """healthcheck() ritorna lista con risultati."""
        registry = Registry()
        registry.carica("infobandi", InfobandiAdapter)
        report = registry.healthcheck()
        assert len(report) == 1
        assert report[0]["nome"] == "infobandi"
        assert report[0]["stato"] in ("ok", "errore")

    def test_carica_doppia_logga(self):
        """Caricare due volte la stessa fonte è permesso (sovrascrive)."""
        registry = Registry()
        registry.carica("infobandi", InfobandiAdapter)
        registry.carica("infobandi", InfobandiAdapter, ttl=9999)
        assert registry._fonti["infobandi"]["ttl"] == 9999
