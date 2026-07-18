"""Test BandoNormalizzato: creazione, hash, validità."""

from datetime import date
from tsi.bandi.base import BandoNormalizzato


class TestBandoNormalizzato:
    def test_minimo(self):
        """Crea bando con solo campi obbligatori."""
        b = BandoNormalizzato(
            titolo="Bando test",
            ente="Ente test",
            scadenza=date(2026, 12, 31),
            budget=None,
            url="https://example.com",
            territorio="Nazionale",
            tags=["minori"],
            descrizione="",
            fonte="test",
            id_fonte="1",
        )
        assert b.valido
        assert b.hash_contenuto  # generato automaticamente

    def test_non_valido(self):
        """Bando senza titolo non è valido."""
        b = BandoNormalizzato(
            titolo="",
            ente="",
            scadenza=None,
            budget=None,
            url="",
            territorio="",
            tags=[],
            descrizione="",
            fonte="test",
            id_fonte="1",
        )
        assert not b.valido

    def test_hash_consistente(self):
        """Stessi dati → stesso hash."""
        b1 = BandoNormalizzato(
            titolo="Bando X", ente="Ente Y",
            scadenza=date(2026, 7, 18), budget=50000.0,
            url="https://a.it", territorio="Nazionale", tags=[],
            descrizione="", fonte="src1", id_fonte="1",
        )
        b2 = BandoNormalizzato(
            titolo="Bando X", ente="Ente Y",
            scadenza=date(2026, 7, 18), budget=50000.0,
            url="https://b.it", territorio="", tags=[],
            descrizione="", fonte="src2", id_fonte="2",
        )
        assert b1.hash_contenuto == b2.hash_contenuto

    def test_hash_diverso(self):
        """Dati diversi → hash diverso."""
        b1 = BandoNormalizzato(
            titolo="Bando A", ente="Ente X",
            scadenza=date(2026, 7, 18), budget=None,
            url="", territorio="", tags=[], descrizione="",
            fonte="t", id_fonte="1",
        )
        b2 = BandoNormalizzato(
            titolo="Bando B", ente="Ente X",
            scadenza=date(2026, 7, 18), budget=None,
            url="", territorio="", tags=[], descrizione="",
            fonte="t", id_fonte="2",
        )
        assert b1.hash_contenuto != b2.hash_contenuto
