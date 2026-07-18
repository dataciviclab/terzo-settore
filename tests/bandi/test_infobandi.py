"""Test adapter Infobandi — healthcheck e normalizzazione."""

from datetime import date
from tsi.bandi.fonti.infobandi import InfobandiAdapter


class TestInfobandiAdapter:
    def setup_method(self):
        self.adapter = InfobandiAdapter()

    def test_health(self):
        """Infobandi API deve essere raggiungibile."""
        ok = self.adapter.health()
        assert ok, "Infobandi API non raggiungibile"

    def test_fetch_restituisce_lista(self):
        """fetch() ritorna lista, anche vuota."""
        bandi = self.adapter.fetch()
        assert isinstance(bandi, list)

    def test_sample_ha_campi_obbligatori(self):
        """I bandi campionati hanno titolo e ente."""
        bandi = self.adapter.sample(3)
        for b in bandi:
            assert b.titolo, f"Bando senza titolo: {b}"
            assert b.ente, f"Bando senza ente: {b}"

    def test_normalizza_scadenza(self):
        """Test parsing date in italiano."""
        tests = [
            ("7 settembre 2026 alle ore 12:00", date(2026, 9, 7)),
            ("16 ottobre 2026 alle ore 13:00", date(2026, 10, 16)),
            ("03 novembre 2026", date(2026, 11, 3)),
            ("08 ottobre 2026 (con proroga) ore 12.00", date(2026, 10, 8)),
            ("2026-12-31", date(2026, 12, 31)),
            ("31/12/2026", date(2026, 12, 31)),
        ]
        for raw, atteso in tests:
            risultato = self.adapter._parse_scadenza(raw)
            assert risultato == atteso, f"{raw} → {risultato} (atteso {atteso})"

    def test_normalizza_scadenza_none(self):
        """Date non parsabili ritornano None."""
        assert self.adapter._parse_scadenza("") is None
        assert self.adapter._parse_scadenza("non una data") is None

    def test_parse_budget(self):
        """Test parsing importi."""
        tests = [
            ("budget di 50.000 euro", 50000.0),
            ("stanziamento complessivo pari a 1.944.818", 1944818.0),
            ("importo 200.000", 200000.0),
            ("budget di 2 milioni di euro", 2000000.0),
        ]
        for testo, atteso in tests:
            risultato = self.adapter._parse_budget(testo)
            assert risultato == atteso, f"'{testo[:30]}' → {risultato} (atteso {atteso})"
