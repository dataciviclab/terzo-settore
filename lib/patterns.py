"""Wrapper backward-compat — importa da lib/temi.py.

Le funzioni e dizionari originali sono stati unificati in lib/temi.py.
Questo file garantisce che gli import esistenti continuino a funzionare.
"""

import re
import unicodedata

from lib.temi import (
    TEMA_PATTERN as TAG_PATTERN,
    SEZIONI_PER_TAG as SECTION_TAG_MAP,
    TEMA_PATTERN as TEXT_KEYWORDS,
    estrai_temi,
    sezioni_per_tag,
)

# Backward compat: funzioni rinominano
extract_tags_from_text = estrai_temi
get_sections_from_tags = sezioni_per_tag

GENERIC_TAGS = {"lavoro", "inclusione", "ricerca", "giovani", "educazione", "salute"}


def get_pattern_from_tags(tags):
    """Costruisce pattern regexp combinato dai tag del bando."""
    tags_lower = set(t.lower() for t in tags)
    specific = {t for t in tags_lower if t not in GENERIC_TAGS}
    specific_validi = {t for t in specific if t in TAG_PATTERN}
    generici_validi = {t for t in tags_lower if t in TAG_PATTERN}
    use_tags = specific_validi if specific_validi else generici_validi
    parts = []
    for tag, pattern in TAG_PATTERN.items():
        if tag in use_tags and pattern:
            parts.append(pattern)
    return "|".join(parts) if parts else None


# ── Dati non tematici (rimangono qui) ──

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
