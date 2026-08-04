#!/usr/bin/env python3
"""Test per normalize_comune: accenti e apostrofi nel join comuni.

Uso: python tests/test_normalize_comune.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
from config import normalize_comune

CASES = [
    # (input, atteso) — accenti e apostrofi normalizzati alla stessa chiave
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
    ("Sant’Angelo", "SANTANGELO"),
    ("Sant'Angelo", "SANTANGELO"),
    ("SantʼElia", "SANTELIA"),
    ("Val d'Aosta", "VAL DAOSTA"),
    ("Val d’Aosta", "VAL DAOSTA"),
    ("Cantù", "CANTU"),
    ("CANTU'", "CANTU"),
    ("Reggio nell'Emilia", "REGGIO NELLEMILIA"),
    ("Bagno a Ripoli", "BAGNO A RIPOLI"),
    ("Barberino di Mugello", "BARBERINO DI MUGELLO"),
    # robustezza: input nulli
    (None, ""),
    ("", ""),
    ("   ", ""),
]


def main():
    failures = 0
    for raw, expected in CASES:
        got = normalize_comune(raw)
        if got != expected:
            failures += 1
            print(f"  FAIL {raw!r} -> {got!r} (atteso {expected!r})")
    if failures:
        print(f"\n❌ {failures}/{len(CASES)} casi falliti")
        sys.exit(1)
    print(f"✅ {len(CASES)} casi passati")
    sys.exit(0)


if __name__ == "__main__":
    main()
