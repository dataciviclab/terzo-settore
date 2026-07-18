"""Test deduplica cross-fonte."""

from datetime import date
from tsi.bandi.base import BandoNormalizzato
from tsi.bandi.dedup import deduplica


class TestDedup:
    def test_nessun_duplicato(self):
        """Bandi diversi non vengono fusi."""
        b1 = BandoNormalizzato(titolo="Bando A", ente="Ente X",
            scadenza=date(2026, 12, 31), budget=1000,
            url="https://a.it", territorio="Nazionale", tags=[],
            descrizione="", fonte="f1", id_fonte="1")
        b2 = BandoNormalizzato(titolo="Bando B", ente="Ente Y",
            scadenza=date(2026, 11, 30), budget=2000,
            url="https://b.it", territorio="Nazionale", tags=[],
            descrizione="", fonte="f2", id_fonte="2")
        assert len(deduplica([b1, b2])) == 2

    def test_stesso_bando_da_due_fonti(self):
        """Stesso bando da due fonti → unico record."""
        b1 = BandoNormalizzato(titolo="Bando X", ente="Ente Z",
            scadenza=date(2026, 7, 18), budget=None,
            url="https://f1.it", territorio="Nazionale", tags=[],
            descrizione="", fonte="f1", id_fonte="x1")
        b2 = BandoNormalizzato(titolo="Bando X", ente="Ente Z",
            scadenza=date(2026, 7, 18), budget=50000,
            url="https://f2.it", territorio="Nazionale", tags=[],
            descrizione="Con descrizione", fonte="f2", id_fonte="x2")
        risultati = deduplica([b1, b2])
        assert len(risultati) == 1
        # Tiene il più ricco: ha budget + descrizione
        assert risultati[0].budget == 50000
        assert risultati[0].descrizione == "Con descrizione"
        assert risultati[0].fonte == "f2"  # il più ricco

    def test_scarta_non_validi(self):
        """Bandi non validi vengono filtrati."""
        b_valido = BandoNormalizzato(titolo="Ok", ente="Ente",
            scadenza=date(2026, 12, 31), budget=None,
            url="", territorio="", tags=[], descrizione="",
            fonte="f1", id_fonte="1")
        b_invalido = BandoNormalizzato(titolo="", ente="",
            scadenza=None, budget=None,
            url="", territorio="", tags=[], descrizione="",
            fonte="f2", id_fonte="2")
        assert len(deduplica([b_valido, b_invalido])) == 1
