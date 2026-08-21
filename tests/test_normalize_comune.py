import pytest

from lib.config import normalize_comune

CASES = [
    ("Città", "CITTA"),
    ("CITTA'", "CITTA"),
    ("Città di Castello", "CITTA DI CASTELLO"),
    ("CITTA' DI CASTELLO", "CITTA DI CASTELLO"),
    ("San Donà di Piave", "SAN DONA DI PIAVE"),
    ("SAN DONA' DI PIAVE", "SAN DONA DI PIAVE"),
    ("Nardò", "NARDO"),
    ("NARDO'", "NARDO"),
    ("Forlì", "FORLI"),
    ("FORLI'", "FORLI"),
    ("Sant'Agata", "SANTAGATA"),
    ("Sant'Angelo", "SANTANGELO"),
    ("Sant'Angelo", "SANTANGELO"),
    ("Sant'Elia", "SANTELIA"),
    ("Val d'Aosta", "VAL DAOSTA"),
    ("Val d'Aosta", "VAL DAOSTA"),
    ("Cantù", "CANTU"),
    ("CANTU'", "CANTU"),
    ("Reggio nell'Emilia", "REGGIO NELLEMILIA"),
    ("Bagno a Ripoli", "BAGNO A RIPOLI"),
    ("Barberino di Mugello", "BARBERINO DI MUGELLO"),
    (None, ""),
    ("", ""),
    ("   ", ""),
    ("Reggio Calabria", "REGGIO DI CALABRIA"),
    ("REGGIO EMILIA", "REGGIO NELLEMILIA"),
    ("Montecatini Terme", "MONTECATINI-TERME"),
    ("Jonadi", "JONADI"),
    ("IONADI", "JONADI"),
    ("Nizza Sicilia", "NIZZA DI SICILIA"),
    ("Cortaccia sulla strada del vin", "CORTACCIA SULLA STRADA DEL VINO"),
]


@pytest.mark.parametrize("raw,expected", CASES, ids=[f"{c[0]!r}" for c in CASES])
def test_normalize_comune(raw, expected):
    assert normalize_comune(raw) == expected
