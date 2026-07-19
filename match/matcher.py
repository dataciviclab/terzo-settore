"""Matching engine: bandi contro ETS."""

import re
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from config import ETS_FILE, INFOBANDI_CAT_MAP, get_province_filter
from temi import (
    estrai_temi as extract_tags_from_text,
    get_pattern_from_tags,
    sezioni_per_tag as get_sections_from_tags,
)

MATCH_ETS_SQL = (ROOT / "ets/match_ets.sql").read_text()

NON_OPERATIVE_TITLE_RE = re.compile(
    r"\b(esito|esiti|approvat[ioe]|affidat[aoie]|aggiudicat[aoie]|risultat[io]|graduatoria|finanziati)\b",
    re.IGNORECASE,
)

TERRITORY_KEYWORDS = {
    "mezzogiorno": ["Mezzogiorno"], "sud italia": ["Mezzogiorno"],
    "basilicata": ["Basilicata"], "calabria": ["Calabria"],
    "campania": ["Campania"], "molise": ["Molise"], "puglia": ["Puglia"],
    "sardegna": ["Sardegna"], "sicilia": ["Sicilia"],
    "lombardia": ["Lombardia"], "piemonte": ["Piemonte"],
    "veneto": ["Veneto"], "emilia-romagna": ["Emilia-Romagna"],
    "emilia romagna": ["Emilia-Romagna"], "toscana": ["Toscana"],
    "lazio": ["Lazio"], "italia": ["Nazionale"], "nazionale": ["Nazionale"],
    "europa": ["Europa"], "unione europea": ["Europa"],
    "ucraina": ["Ucraina"], "libia": ["Libia"], "mediterraneo": ["Mediterraneo"],
}


def extract_territory(b):
    raw = b.get("territorio", [])
    if isinstance(raw, str):
        raw = [raw]
    territories = {str(t).strip().title() for t in raw if str(t).strip()}
    text = " ".join(str(b.get(k, "") or "") for k in ("titolo", "descrizione", "obiettivi", "ammissibili"))
    text_lower = text.lower()
    for needle, labels in TERRITORY_KEYWORDS.items():
        if needle in text_lower:
            territories.update(labels)
    if not territories:
        territories.add("Nazionale/da verificare")
    return sorted(territories)


def classify_bando(b, scadenza, gg_rimasti):
    title = str(b.get("titolo", b.get("title", "")) or "")
    scadenza_str = str(b.get("scadenza", "") or "")
    if b.get("scaduto") is True or (scadenza and gg_rimasti < 0):
        return "scaduto", "scaduto"
    if NON_OPERATIVE_TITLE_RE.search(title):
        return "notizia/esito", "titolo non operativo"
    if scadenza:
        return "attivo", "scadenza valida"
    if re.search(r"\bsportello\b|finestre|fino ad esaurimento", scadenza_str, re.IGNORECASE):
        return "sportello", "procedura a sportello o finestre multiple"
    return "senza data", "scadenza non parsabile"


def normalise_bando(b):
    titolo = b.get("titolo", b.get("title", ""))
    url = b.get("url", "")
    scadenza_str = b.get("scadenza", "")
    ente = b.get("ente_erogatore", b.get("donatore", ""))
    fonte = b.get("_fonte", "unknown")

    tags = b.get("tag", b.get("tags", []))
    if isinstance(tags, str):
        tags = [tags]

    if fonte == "info_cooperazione":
        testo = b.get("testo_nlp", "") or b.get("descrizione", "") or ""
        tags_nlp = extract_tags_from_text(testo) if testo else []
        testo_lower = testo.lower()
        nativi_validi = set()
        for kw in tags:
            kw_clean = kw.strip().lower()
            if kw_clean in testo_lower:
                tag_map = {"inclusione": "inclusione sociale"}
                nativi_validi.add(tag_map.get(kw_clean, kw_clean))
        tags = list(set(tags_nlp) | nativi_validi)
    else:
        if not tags:
            tags_nlp = extract_tags_from_text(titolo)
            if tags_nlp:
                tags = tags_nlp
            for cat_id in b.get("categorie", []):
                tag_from_cat = INFOBANDI_CAT_MAP.get(cat_id)
                if tag_from_cat and tag_from_cat not in tags:
                    tags.append(tag_from_cat)

    territorio = extract_territory(b)
    return titolo, url, scadenza_str, ente, tags, territorio, fonte


def is_sport_bando(tags):
    return any((t or "").strip().lower() == "sport" for t in tags)


def match_bando(con, pattern, tags, limit=10, territorio=None):
    sections = get_sections_from_tags(tags)
    sezioni_quote = ", ".join(f"'{s}'" for s in sections) if sections else "''"

    sport_fallback = is_sport_bando(tags)
    parts = []
    if sport_fallback:
        parts.append("ha_sport_in_denominazione")
    if sections:
        parts.append(f"sezione IN ({sezioni_quote})")
    match_condition = " OR ".join(parts) if parts else "1=0"

    sez_match_bool = "FALSE"
    if sections:
        sez_match_bool = f"sezione IN ({sezioni_quote})"

    province_filtro = get_province_filter(territorio)
    province_filter = ""
    if province_filtro:
        prov_quote = ", ".join(f"'{p}'" for p in province_filtro)
        province_filter = f"AND provincia IN ({prov_quote})"

    tags_lower = set(t.lower() for t in tags)
    section_bonuses = []
    if "volontariato" in tags_lower:
        section_bonuses.append("+ CASE WHEN sezione = 'ORGANIZZAZIONI DI VOLONTARIATO' THEN 5 ELSE 0 END")
    if "sport" in tags_lower:
        section_bonuses.append("+ CASE WHEN sezione = 'ASSOCIAZIONI DI PROMOZIONE SOCIALE' THEN 5 ELSE 0 END")
    if "lavoro" in tags_lower or "formazione" in tags_lower:
        section_bonuses.append("+ CASE WHEN sezione = 'IMPRESI SOCIALI' THEN 5 ELSE 0 END")
    section_bonus = " ".join(section_bonuses)

    match_tema = f"(regexp_matches(lower(denominazione), '{pattern}') OR regexp_matches(temi_anac, '{pattern}'))"

    sql = MATCH_ETS_SQL.format(
        ets_file=ETS_FILE,
        match_condition=match_condition,
        match_tema=match_tema,
        sport_bonus="TRUE" if sport_fallback else "FALSE",
        sez_match_bool=sez_match_bool,
        section_bonus=section_bonus,
        province_filter=province_filter,
        limit=limit,
    )
    return con.sql(sql).fetchdf()
