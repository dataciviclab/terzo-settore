"""Paths, thresholds e costanti del sistema."""

import re
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Dataset
ETS_FILE = ROOT / "data/unified_ets.parquet"

# Bandi
BANDI_FILES = [
    ROOT / "data/bandi/infobandi_bandi.json",
    ROOT / "data/bandi/info_cooperazione_bandi.json",
    ROOT / "data/bandi/indicebandi_bandi.json",
]

MESI_IT = {
    "gennaio": "01", "febbraio": "02", "marzo": "03", "aprile": "04",
    "maggio": "05", "giugno": "06", "luglio": "07", "agosto": "08",
    "settembre": "09", "ottobre": "10", "novembre": "11", "dicembre": "12",
}


def parse_scadenza(raw: str) -> date | None:
    """Parsa una scadenza in formato italiano o ISO."""
    if not raw:
        return None
    s = raw.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    m = re.match(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})", s, re.IGNORECASE)
    if m:
        g, me, a = m.group(1), m.group(2).lower(), m.group(3)
        if me in MESI_IT:
            try:
                return date(int(a), int(MESI_IT[me]), int(g))
            except ValueError:
                return None
    return None


def filtra_bandi_attivi(bandi: list[dict]) -> list[dict]:
    """Filtra bandi scaduti e notizie/esiti.

    Chiamato da ogni aggregatore PRIMA di salvare il JSON.
    """
    oggi = date.today()
    puliti = []
    NON_OPERATIVI = re.compile(
        r"\b(esito|esiti|graduatoria|aggiudicat[aoie]|finanziati|risultat[io])\b",
        re.IGNORECASE,
    )

    for b in bandi:
        # Escludi notizie/esiti
        titolo = str(b.get("titolo", b.get("title", "")) or "")
        if NON_OPERATIVI.search(titolo):
            continue

        # Escludi scaduti
        if b.get("scaduto") is True:
            continue

        scadenza_raw = b.get("scadenza")
        if scadenza_raw:
            scad = parse_scadenza(scadenza_raw)
            if scad and scad < oggi:
                continue

        puliti.append(b)

    return puliti

# Output
RADAR_REPORT = ROOT / "cruscotto/radar-completo.md"

# Soglie capacità (usate in build_unified_ets.sql)
CAP_GRANT_UE = 0
CAP_AIUTI_STATO = 0
CAP_PNRR = 0
CAP_CINQUE_SINGOLO = 10000
CAP_CINQUE_ANNI = 3
CAP_OC_BILANCIO = 100000
CAP_OC_PROGETTI = 3
CAP_OC_DIPENDENTI = 3
