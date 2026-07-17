"""Core radar logic shared by report views."""

import json
import math
import re
import sys
from datetime import date, datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from config import BANDI_FILES, ETS_FILE
from patterns import (
    INFOBANDI_CAT_MAP,
    extract_tags_from_text,
    get_pattern_from_tags,
    get_sections_from_tags,
    get_province_filter,
)
from html_utils import arricchisci

MONTH_MAP = {
    "gennaio": "01",
    "febbraio": "02",
    "marzo": "03",
    "aprile": "04",
    "maggio": "05",
    "giugno": "06",
    "luglio": "07",
    "agosto": "08",
    "settembre": "09",
    "ottobre": "10",
    "novembre": "11",
    "dicembre": "12",
}

NON_OPERATIVE_TITLE_RE = re.compile(
    r"\b(esito|esiti|approvat[ioe]|affidat[aoie]|aggiudicat[aoie]|risultat[io]|graduatoria|finanziati)\b",
    re.IGNORECASE,
)

TERRITORY_KEYWORDS = {
    "mezzogiorno": ["Mezzogiorno"],
    "sud italia": ["Mezzogiorno"],
    "basilicata": ["Basilicata"],
    "calabria": ["Calabria"],
    "campania": ["Campania"],
    "molise": ["Molise"],
    "puglia": ["Puglia"],
    "sardegna": ["Sardegna"],
    "sicilia": ["Sicilia"],
    "lombardia": ["Lombardia"],
    "piemonte": ["Piemonte"],
    "veneto": ["Veneto"],
    "emilia-romagna": ["Emilia-Romagna"],
    "emilia romagna": ["Emilia-Romagna"],
    "toscana": ["Toscana"],
    "lazio": ["Lazio"],
    "italia": ["Nazionale"],
    "nazionale": ["Nazionale"],
    "europa": ["Europa"],
    "unione europea": ["Europa"],
    "ucraina": ["Ucraina"],
    "libia": ["Libia"],
    "mediterraneo": ["Mediterraneo"],
}

MATCH_ETS_SQL = """
    SELECT codice_fiscale, denominazione, comune, provincia, capacita_progettuale,
           cinque_2025, flag_sport_denom, sezione,
           ha_grant_ue, ha_pnrr,
           CASE
             WHEN regexp_matches(lower(denominazione), '{pattern}') AND flag_sport_denom AND {sez_match_bool} THEN 'tema+sport+sezione'
             WHEN regexp_matches(lower(denominazione), '{pattern}') AND flag_sport_denom THEN 'tema+sport'
             WHEN regexp_matches(lower(denominazione), '{pattern}') AND {sez_match_bool} THEN 'tema+sezione'
             WHEN regexp_matches(lower(denominazione), '{pattern}') THEN 'tema denominazione'
             WHEN flag_sport_denom THEN 'sport da denominazione'
             WHEN {sez_match_bool} THEN 'sezione'
             ELSE 'match'
           END AS motivo_match,
           (
             -- Match tematico (0-60) — PESO PRINCIPALE
             CASE WHEN regexp_matches(lower(denominazione), '{pattern}') THEN 60 ELSE 0 END
             -- Match per sezione (0-25) — SECONDO PESO
             + CASE WHEN {sez_match_bool} THEN 25 ELSE 0 END
             -- Sport bonus (0-15)
             + CASE WHEN flag_sport_denom AND {sport_bonus} THEN 15 ELSE 0 END
             {section_bonus}
             -- Capacità progettuale (0-20) — peso ridotto
             + CASE capacita_progettuale
                 WHEN 'alta' THEN 20
                 WHEN 'medio-alta' THEN 15
                 WHEN 'media' THEN 10
                 ELSE 0
               END
             -- 5x1000 (0-15) — peso leggermente ridotto
             + CASE
                 WHEN cinque_2025 >= 100000 THEN 15
                 WHEN cinque_2025 >= 10000 THEN 10
                 WHEN cinque_2025 > 0 THEN 5
                 ELSE 0
               END
             -- Grant UE (0-8) — peso ridotto
             + CASE WHEN ha_grant_ue THEN 8 ELSE 0 END
             -- PNRR (0-5) — peso ridotto
             + CASE WHEN ha_pnrr THEN 5 ELSE 0 END
             -- Impresa Sociale (0-5) — invariato
             + CASE WHEN sezione = 'IMPRESI SOCIALI' THEN 5 ELSE 0 END
           ) AS score
    FROM '{ets_file}'
    WHERE {match_condition}
      AND capacita_progettuale IN ('media', 'medio-alta', 'alta')
      {province_filter}
    ORDER BY score DESC, cinque_2025 DESC NULLS LAST
    LIMIT {limit}
"""


def parse_date_flex(s):
    oggi = date.today()
    if not s:
        return None, 999
    s = s.strip().lower()
    m = re.match(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})", s)
    if m:
        giorno, mese, anno = m.groups()
        mese_num = MONTH_MAP.get(mese)
        if mese_num:
            try:
                d = date(int(anno), int(mese_num), int(giorno))
                return d, (d - oggi).days
            except ValueError:
                pass
    try:
        d = datetime.strptime(s, "%d/%m/%Y").date()
        return d, (d - oggi).days
    except ValueError:
        pass
    return None, 999


def is_missing(value):
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).lower() == "nan"


def fmt_text(value, default="-"):
    return default if is_missing(value) else str(value)


def fmt_euro(value):
    if is_missing(value):
        return "-"
    return f"€{value:,.0f}"


def fmt_tags(tags):
    return ", ".join(tags) if tags else "-"


def fmt_match_reason(c):
    motivo = c.get("motivo_match", "match")
    # Mappa i nuovi motivi in versione leggibile
    motivo_map = {
        "tema+sport+sezione": "match tema + sport + sezione",
        "tema+sport": "match tema + sport",
        "tema+sezione": "match tema + sezione",
        "tema denominazione": "match su denominazione",
        "sport da denominazione": "sport da denominazione",
        "sezione": "match su sezione",
        "match": "match",
    }
    parts = [motivo_map.get(motivo, motivo)]
    cap = c.get("capacita_progettuale")
    if cap:
        parts.append(f"capacità {cap}")
    cinque = c.get("cinque_2025")
    if not is_missing(cinque):
        if cinque >= 100000:
            parts.append("5x1000 >100k")
        elif cinque >= 10000:
            parts.append("5x1000 >10k")
        elif cinque > 0:
            parts.append("5x1000 presente")
    if c.get("ha_grant_ue") is True:
        parts.append("grant UE")
    if c.get("ha_pnrr") is True:
        parts.append("PNRR")
    sez = c.get("sezione")
    if sez == "IMPRESE SOCIALI":
        parts.append("Impresa Sociale")
    elif sez == "ORGANIZZAZIONI DI VOLONTARIATO":
        parts.append("ODV")
    elif sez == "ASSOCIAZIONI DI PROMOZIONE SOCIALE":
        parts.append("APS")
    return "; ".join(parts)


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


def deduplicate_bandi(bandi):
    unique = []
    seen_urls = set()
    seen_titles = set()
    for b in sorted(bandi, key=lambda x: len(x.get("tag", x.get("tags", [])) or []), reverse=True):
        titolo_b = (b.get("titolo", b.get("title", "")) or "").strip().lower()
        url_b = (b.get("url", "") or "").strip()
        if url_b and url_b in seen_urls:
            continue
        if titolo_b in seen_titles:
            continue
        dup = False
        for t in seen_titles:
            if len(titolo_b) > 15 and len(t) > 15:
                if any(titolo_b[i : i + 25] in t for i in range(len(titolo_b) - 24)):
                    dup = True
                    break
        if dup:
            continue
        seen_urls.add(url_b)
        seen_titles.add(titolo_b)
        unique.append(b)
    return unique


def load_bandi(files=None):
    bandi = []
    for fpath in files or BANDI_FILES:
        try:
            with open(fpath, encoding="utf-8") as f:
                raw = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        fonte = "infobandi" if "infobandi" in fpath.name else "info_cooperazione"
        if isinstance(raw, list):
            for b in raw:
                b["_fonte"] = fonte
            bandi.extend(raw)
        elif isinstance(raw, dict) and "bandi" in raw:
            for b in raw["bandi"]:
                b["_fonte"] = fonte
            bandi.extend(raw["bandi"])
    return deduplicate_bandi(bandi)


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
        # Strategia mista: NLP sul testo + nativi validati (solo keyword nel testo)
        testo = b.get("testo_nlp", "") or b.get("descrizione", "") or ""
        tags_nlp = extract_tags_from_text(testo) if testo else []
        
        # Nativi validati: keyword che appaiono ANCHE nel testo (filtra rumore HTML)
        testo_lower = testo.lower()
        nativi_validi = set()
        for kw in tags:
            kw_clean = kw.strip().lower()
            if kw_clean in testo_lower:
                # Mappa keyword nativo → tag standard (es. "inclusione" → "inclusione sociale")
                tag_map = {
                    "inclusione": "inclusione sociale",
                }
                nativi_validi.add(tag_map.get(kw_clean, kw_clean))
        
        tags = list(set(tags_nlp) | nativi_validi)
    else:
        # Infobandi: tag nativi + NLP fallback (logica attuale)
        if not tags:
            tags_nlp = extract_tags_from_text(titolo)
            if tags_nlp:
                tags = tags_nlp
            categorie = b.get("categorie", [])
            if categorie:
                for cat_id in categorie:
                    tag_from_cat = INFOBANDI_CAT_MAP.get(cat_id)
                    if tag_from_cat and tag_from_cat not in tags:
                        tags.append(tag_from_cat)
    
    territorio = extract_territory(b)
    return titolo, url, scadenza_str, ente, tags, territorio, fonte


def is_sport_bando(tags):
    return any((t or "").strip().lower() == "sport" for t in tags)


def match_bando(con, pattern, tags, limit=10, territorio=None):
    # — Mossa 1: sezioni pertinenti dal tag —
    sections = get_sections_from_tags(tags)
    sezioni_quote = ", ".join(f"'{s}'" for s in sections) if sections else "''"

    # — Gate condizione: denominazione matcha O sport fallback O sezione pertinente —
    sport_fallback = is_sport_bando(tags)
    match_condition = f"(regexp_matches(lower(denominazione), '{pattern}')"
    if sport_fallback:
        match_condition += " OR flag_sport_denom"
    if sections:
        match_condition += f" OR sezione IN ({sezioni_quote})"
    match_condition += ")"

    # — Sezione match bool (per CASE e score) —
    sez_match_bool = "FALSE"
    if sections:
        sez_match_bool = f"sezione IN ({sezioni_quote})"

    # — Mossa 3: filtro geografico da provincia —
    province_filtro = get_province_filter(territorio)
    province_filter = ""
    if province_filtro:
        prov_quote = ", ".join(f"'{p}'" for p in province_filtro)
        province_filter = f"AND provincia IN ({prov_quote})"

    # — Bonus per sezione legacy (mantenuti per retrocompatibilità, ma peso minore) —
    tags_lower = set(t.lower() for t in tags)
    section_bonuses = []
    if "volontariato" in tags_lower:
        section_bonuses.append("+ CASE WHEN sezione = 'ORGANIZZAZIONI DI VOLONTARIATO' THEN 5 ELSE 0 END")
    if "sport" in tags_lower:
        section_bonuses.append("+ CASE WHEN sezione = 'ASSOCIAZIONI DI PROMOZIONE SOCIALE' THEN 5 ELSE 0 END")
    if "lavoro" in tags_lower or "formazione" in tags_lower:
        section_bonuses.append("+ CASE WHEN sezione = 'IMPRESI SOCIALI' THEN 5 ELSE 0 END")
    section_bonus = " ".join(section_bonuses)

    sql = MATCH_ETS_SQL.format(
        ets_file=ETS_FILE,
        pattern=pattern,
        match_condition=match_condition,
        sport_bonus="TRUE" if sport_fallback else "FALSE",
        sez_match_bool=sez_match_bool,
        section_bonus=section_bonus,
        province_filter=province_filter,
        limit=limit,
    )
    return con.sql(sql).fetchdf()


def run_scan(con=None, bandi=None, match_limit=10, include_statuses=None):
    con = con or duckdb.connect()
    bandi = bandi or load_bandi()
    include_statuses = include_statuses or {"attivo", "sportello"}

    resultados = []
    sin_match = []
    skipped = []
    stats_ets = set()

    for b in bandi:
        titolo, url, scadenza_str, ente, tags, territorio, fonte = normalise_bando(b)
        scadenza, gg_rimasti = parse_date_flex(scadenza_str)
        status, status_motivo = classify_bando(b, scadenza, gg_rimasti)
        if status not in include_statuses:
            skipped.append(
                {
                    "titolo": titolo,
                    "url": url,
                    "ente": ente,
                    "scadenza": scadenza_str,
                    "status": status,
                    "motivo": status_motivo,
                }
            )
            continue

        # Per info-cooperazione senza tag: prova ad arricchire con pagina singola
        if fonte == "info_cooperazione" and not tags:
            testo_corto = b.get("testo_nlp", "") or b.get("descrizione", "") or ""
            if len(testo_corto) < 500 and url:
                extra = arricchisci(url)
                testo_lungo = extra.get("testo_nlp", "")
                if len(testo_lungo) > len(testo_corto):
                    nlp_tags = extract_tags_from_text(testo_lungo)
                    if nlp_tags:
                        tags = nlp_tags
                        b["testo_nlp"] = testo_lungo  # aggiorna per uso futuro

        # Budget: da cache o HTML fallback (solo se non già presente)
        if not b.get("budget") and url:
            extra = arricchisci(url)
            if extra.get("budget"):
                b["budget"] = extra["budget"]
            if extra.get("territorio"):
                if not territorio or territorio == ["Nazionale/da verificare"]:
                    territorio = extra["territorio"]

        pattern = get_pattern_from_tags(tags)
        if not pattern:
            # Anche senza pattern, proviamo il match per sezione
            sections = get_sections_from_tags(tags)
            if not sections:
                sin_match.append((titolo, url, ente, scadenza_str, gg_rimasti, tags, territorio, status, "nessun pattern tag"))
                continue
            pattern = ".*"  # matcha tutto, il filtro è sulla sezione

        df = match_bando(con, pattern, tags, limit=match_limit, territorio=territorio)
        if df.empty:
            sin_match.append((titolo, url, ente, scadenza_str, gg_rimasti, tags, territorio, status, "nessun ETS matcha"))
            continue

        if "codice_fiscale" in df.columns:
            stats_ets.update(df["codice_fiscale"].tolist())
        resultados.append(
            {
                "titolo": titolo,
                "url": url,
                "ente": ente,
                "budget": b.get("budget"),
                "scadenza": scadenza_str,
                "gg": gg_rimasti,
                "tags": tags,
                "territorio": territorio,
                "status": status,
                "pattern": pattern,
                "candidati": df.to_dict("records"),
            }
        )

    return {
        "bandi": bandi,
        "resultados": resultados,
        "sin_match": sin_match,
        "skipped": skipped,
        "stats_ets": stats_ets,
    }
