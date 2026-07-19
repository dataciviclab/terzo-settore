"""Paths, thresholds e costanti del sistema."""

import re
import unicodedata
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


def normalizza_scadenza(raw: str) -> str | None:
    """Normalizza una scadenza in YYYY-MM-DD (stringa), o None."""
    if not raw:
        return None
    s = re.sub(r"\s+alle\s+ore\s+[\d:.]+", "", raw)
    s = re.sub(r"\s*\([^)]*\)\s*", " ", s)
    s = re.sub(r"\s+ore\s+[\d:.]+", "", s)
    d = parse_scadenza(s)
    return d.strftime("%Y-%m-%d") if d else None


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

# Dati geografici (regioni → province)
REGION_PROVINCES = {
    "Abruzzo": ["AQ", "CH", "PE", "TE"],
    "Basilicata": ["PZ", "MT"],
    "Calabria": ["CZ", "CS", "KR", "RC", "VV"],
    "Campania": ["AV", "BN", "CE", "NA", "SA"],
    "Emilia-Romagna": ["BO", "FE", "FC", "MO", "PC", "PR", "RA", "RE", "RN"],
    "Friuli Venezia Giulia": ["GO", "PN", "TS", "UD"],
    "Lazio": ["FR", "LT", "RI", "RM", "VT"],
    "Liguria": ["GE", "IM", "SP", "SV"],
    "Lombardia": ["BG", "BS", "CO", "CR", "LC", "LO", "MB", "MI", "MN", "PV", "SO", "VA"],
    "Marche": ["AN", "AP", "FM", "MC", "PU"],
    "Molise": ["CB", "IS"],
    "Piemonte": ["AL", "AT", "BI", "CN", "NO", "TO", "VB", "VC"],
    "Puglia": ["BA", "BR", "BT", "FG", "LE", "TA"],
    "Sardegna": ["CA", "NU", "OR", "SS", "SU"],
    "Sicilia": ["AG", "CL", "CT", "EN", "ME", "PA", "RG", "SR", "TP"],
    "Toscana": ["AR", "FI", "GR", "LI", "LU", "MS", "PI", "PO", "PT", "SI"],
    "Trentino Alto Adige": ["BZ", "TN"],
    "Umbria": ["PG", "TR"],
    "Valle d'Aosta": ["AO"],
    "Veneto": ["BL", "PD", "RO", "TV", "VE", "VI", "VR"],
}

MEZZOGIORNO_PROVINCES = (
    REGION_PROVINCES["Abruzzo"] + REGION_PROVINCES["Basilicata"]
    + REGION_PROVINCES["Calabria"] + REGION_PROVINCES["Campania"]
    + REGION_PROVINCES["Molise"] + REGION_PROVINCES["Puglia"]
    + REGION_PROVINCES["Sardegna"] + REGION_PROVINCES["Sicilia"]
)

INFOBANDI_CAT_MAP = {
    1200: "giovani", 1199: "volontariato", 803: "volontariato",
    1201: "cultura", 1234: "diritti", 1434: "migranti",
    1213: "lavoro", 130: "giovani", 81: "sport",
    1203: "migranti", 1206: "ambiente", 1208: "giustizia",
    1204: "ricerca", 128: "cultura", 127: "cooperazione internazionale",
}


def get_province_filter(territorio):
    if not territorio:
        return []
    provinces = []
    for t in territorio:
        t_clean = t.strip().title()
        if t_clean == "Mezzogiorno":
            return list(MEZZOGIORNO_PROVINCES)
        if t_clean in REGION_PROVINCES:
            provinces.extend(REGION_PROVINCES[t_clean])
    return provinces


def normalize_comune(nome):
    if not nome:
        return ""
    nome = unicodedata.normalize("NFD", nome.strip().upper())
    nome = nome.replace("'", "").replace("`", "").replace("´", "")
    nome = re.sub(r"\s+", " ", nome).strip()
    return nome.replace("'", "").replace("`", "").replace("´", "")
