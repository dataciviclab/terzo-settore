"""Data sources — legge dai nuovi compose (una tabella per fonte)."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from lab_connectors.duckdb import safe_connect

ROOT = Path(__file__).parent.parent
OUT = ROOT / "out" / "data"

# -- Path dei compose ---------------------------------------------------
RUNTS = OUT / "clean" / "runts" / "2026" / "runts_2026_clean.parquet"
RUNTS_SEZIONE = OUT / "mart" / "runts" / "2026" / "runts_sezione.parquet"

MART_ETS = OUT / "mart" / "ets_unified" / "2026" / "ets_unified.parquet"
MART_COMUNI = OUT / "mart" / "ets_unified" / "2026" / "ets_comuni.parquet"

MART_5XMILLE = OUT / "mart" / "ets_5xmille" / "2026" / "ets_5xmille.parquet"
MART_ANAC_AGG = OUT / "mart" / "ets_anac" / "2026" / "ets_anac_aggiudicazioni.parquet"
MART_ANAC_PAR = OUT / "mart" / "ets_anac" / "2026" / "ets_anac_partecipazioni.parquet"
MART_ANAC_SUB = OUT / "mart" / "ets_anac" / "2026" / "ets_anac_subappalti.parquet"
MART_PNRR = OUT / "mart" / "ets_pnrr" / "2026" / "ets_pnrr.parquet"
MART_RNA = OUT / "mart" / "ets_rna" / "2026" / "ets_rna.parquet"
MART_FTS = OUT / "mart" / "ets_fts" / "2026" / "ets_fts.parquet"
MART_MEF = OUT / "mart" / "ets_mef" / "2026" / "ets_mef.parquet"
MART_COESIONE = OUT / "mart" / "ets_opencoesione" / "2026" / "ets_coesione.parquet"

# -- ISTAT Censimento Non Profit 2023 ------------------------------------
ISTAT_2023_CLEAN = OUT / "clean" / "istat_non_profit_2023" / "2023" / "istat_non_profit_2023_2023_clean.parquet"
ISTAT_2023_REGIONI = OUT / "mart" / "istat_non_profit_2023" / "2023" / "nonprofit_by_regione.parquet"
ISTAT_2023_PROVINCE = OUT / "mart" / "istat_non_profit_2023" / "2023" / "nonprofit_by_provincia.parquet"
ISTAT_2023_SETTORI = OUT / "mart" / "istat_non_profit_2023" / "2023" / "nonprofit_by_settore.parquet"

# Clean layers per dettagli
CLEAN_RNA = OUT / "clean" / "ets_rna" / "2026" / "ets_rna_2026_clean.parquet"
CLEAN_PNRR = OUT / "clean" / "ets_pnrr" / "2026" / "ets_pnrr_2026_clean.parquet"
CLEAN_FTS = OUT / "clean" / "ets_fts" / "2026" / "ets_fts_2026_clean.parquet"
CLEAN_ANAC = OUT / "clean" / "ets_anac" / "2026" / "ets_anac_2026_clean.parquet"
CLEAN_MEF = OUT / "clean" / "ets_mef" / "2026" / "ets_mef_2026_clean.parquet"


def _q(sql, path):
    """Esegui SQL su un parquet locale. Usa safe_connect per config consistente."""
    from lab_connectors.duckdb import safe_connect
    with safe_connect() as con:
        return con.sql(sql.replace("_T_", f"read_parquet('{path}')")).df()


# -- Panoramica ---------------------------------------------------------

@st.cache_data(ttl=3600)
def kpi_nazionali():
    r = _q("SELECT COUNT(*) as totale FROM _T_", RUNTS)
    return int(r.iloc[0]["totale"])

@st.cache_data(ttl=3600)
def kpi_con_5xmille():
    r = _q("SELECT COUNT(*) as totale FROM _T_ WHERE importo_5x1000_2025 > 0", MART_ETS)
    return int(r.iloc[0]["totale"])

@st.cache_data(ttl=3600)
def kpi_con_appalti():
    r = _q("SELECT COUNT(*) as totale FROM _T_ WHERE numero_appalti > 0", MART_ETS)
    return int(r.iloc[0]["totale"])

@st.cache_data(ttl=3600)
def kpi_con_aiuti():
    r = _q("SELECT COUNT(*) as totale FROM _T_ WHERE importo_aiuti_stato > 0", MART_ETS)
    return int(r.iloc[0]["totale"])

@st.cache_data(ttl=3600)
def n_ets_con_coesione():
    r = _q("SELECT COUNT(*) as totale FROM _T_ WHERE ha_progetti_coesione", MART_COESIONE)
    return int(r.iloc[0]["totale"])

@st.cache_data(ttl=3600)
def fondi_per_fonte():
    """Riepilogo fondi per fonte (legge da ogni mart singolarmente)."""
    import pandas as pd
    rows = []
    
    for label, path, imp_col in [
        ("5×1000", MART_5XMILLE, "importo_totale"),
        ("Grant UE", MART_FTS, "importo_totale"),
        ("RNA", MART_RNA, "importo_totale"),
        ("PNRR", MART_PNRR, "importo_totale"),
        ("ANAC", MART_ANAC_AGG, "importo_totale"),
    ]:
        try:
            df = _q(f"SELECT COUNT(*) as enti, ROUND(SUM({imp_col}),0) as importo FROM _T_", path)
            rows.append({"fonte": label, "enti": int(df.iloc[0]["enti"]), "importo": float(df.iloc[0]["importo"] or 0)})
        except Exception: pass
    
    # Coesione (no importo)
    try:
        df = _q("SELECT COUNT(*) as enti FROM _T_ WHERE ha_progetti_coesione", MART_COESIONE)
        rows.append({"fonte": "Coesione", "enti": int(df.iloc[0]["enti"]), "importo": 0})
    except Exception: pass
    
    return pd.DataFrame(rows)

@st.cache_data(ttl=3600)
def capacita_progettuale():
    return _q("""
        SELECT capacita_progettuale as livello, COUNT(*) as enti
        FROM _T_ GROUP BY livello ORDER BY livello
    """, MART_ETS)

@st.cache_data(ttl=3600)
def top_ets_5xmille():
    return _q("""
        SELECT denominazione, comune, provincia, capacita_progettuale,
               ROUND(importo_5x1000_2025, 0) as importo_5x1000_2025
        FROM _T_
        WHERE importo_5x1000_2025 > 0
        ORDER BY importo_5x1000_2025 DESC LIMIT 15
    """, MART_ETS)


# -- Anagrafe -----------------------------------------------------------

@st.cache_data(ttl=3600)
def anagrafe_enti(comune: str = None, prov: str = None, sezione: str = None, search: str = None, limit: int = 200):
    where = []
    if comune:
        where.append(f"lower(comune) = '{comune.lower().replace(chr(39),'')}'")
    if prov:
        where.append(f"upper(provincia) = '{prov.upper()}'")
    if sezione:
        where.append(f"sezione = '{sezione}'")
    if search:
        s = search.replace("'", "''")
        where.append(f"(denominazione LIKE '%{s}%' OR codice_fiscale LIKE '%{s}%')")
    w = " WHERE " + " AND ".join(where) if where else ""
    return _q(f"""
        SELECT codice_fiscale, denominazione, sezione, comune, provincia, data_iscrizione
        FROM _T_ {w} ORDER BY denominazione LIMIT {limit}
    """, RUNTS)

@st.cache_data(ttl=3600)
def elenco_sezioni():
    return _q("SELECT DISTINCT sezione FROM _T_ ORDER BY sezione", RUNTS)


# -- 5x1000 -------------------------------------------------------------

@st.cache_data(ttl=3600)
def cinque_per_anno():
    """Trend 5x1000 anno per anno (da COMPOSE long)."""
    return _q("""
        SELECT anno, COUNT(DISTINCT cf) as n_ets,
               ROUND(SUM(importo), 0) as importo_totale,
               ROUND(AVG(importo), 0) as importo_medio
        FROM _T_ WHERE fonte = '5x1000'
        GROUP BY anno ORDER BY anno
    """, OUT / "clean" / "ets_unified" / "2026" / "ets_unified_2026_clean.parquet")

@st.cache_data(ttl=3600)
def cinque_per_tipologia():
    """Distribuzione 5x1000 per flag tematici (da mart 5xmille)."""
    return _q("""
        SELECT
            SUM(CASE WHEN flag_asd THEN 1 ELSE 0 END) as asd,
            SUM(CASE WHEN flag_ricerca_scientifica THEN 1 ELSE 0 END) as ricerca_scientifica,
            SUM(CASE WHEN flag_ricerca_sanitaria THEN 1 ELSE 0 END) as ricerca_sanitaria,
            SUM(CASE WHEN flag_beni_culturali THEN 1 ELSE 0 END) as beni_culturali,
            SUM(CASE WHEN flag_area_protetta THEN 1 ELSE 0 END) as area_protetta,
            SUM(CASE WHEN flag_comune THEN 1 ELSE 0 END) as comuni,
            COUNT(*) as totale
        FROM _T_
    """, MART_5XMILLE)

@st.cache_data(ttl=3600)
def top_ets_5x1000():
    return _q("""
        SELECT codice_fiscale as cf, denominazione, comune, provincia,
               importo_totale, anni, flag_asd, flag_ricerca_scientifica
        FROM _T_ ORDER BY importo_totale DESC LIMIT 20
    """, MART_5XMILLE)


# -- Trasparenza --------------------------------------------------------

@st.cache_data(ttl=3600)
def top_soggetti_concedenti(top_n: int = 20):
    return _q(f"""
        SELECT soggetto_concedente,
               COUNT(DISTINCT codice_fiscale) as n_beneficiari,
               COUNT(*) as n_concessioni,
               ROUND(SUM(importo), 0) as importo_totale
        FROM _T_
        WHERE soggetto_concedente IS NOT NULL AND soggetto_concedente != ''
        GROUP BY soggetto_concedente
        ORDER BY importo_totale DESC LIMIT {top_n}
    """, CLEAN_RNA)

@st.cache_data(ttl=3600)
def rna_per_procedimento():
    return _q("""
        SELECT COALESCE(procedimento, 'Non specificato') as procedimento,
               COUNT(DISTINCT codice_fiscale) as n_beneficiari,
               ROUND(SUM(importo), 0) as importo_totale
        FROM _T_
        GROUP BY procedimento ORDER BY importo_totale DESC
    """, CLEAN_RNA)

@st.cache_data(ttl=3600)
def top_stazioni_appaltanti(top_n: int = 20):
    return _q(f"""
        SELECT stazione_appaltante,
               COUNT(DISTINCT codice_fiscale) as n_ets,
               COUNT(*) as n_appalti,
               ROUND(SUM(importo), 0) as importo_totale
        FROM _T_
        WHERE fonte = 'anac_aggiudicazione'
          AND stazione_appaltante IS NOT NULL AND stazione_appaltante != ''
        GROUP BY stazione_appaltante
        ORDER BY importo_totale DESC LIMIT {top_n}
    """, CLEAN_ANAC)


# -- Programmi ----------------------------------------------------------

@st.cache_data(ttl=3600)
def pnrr_per_programma():
    return _q("""
        SELECT programma, descrizione_missione,
               COUNT(DISTINCT codice_fiscale) as n_ets,
               ROUND(SUM(importo), 0) as fin_totale
        FROM _T_
        GROUP BY programma, descrizione_missione
        ORDER BY fin_totale DESC
    """, CLEAN_PNRR)

@st.cache_data(ttl=3600)
def fts_per_programma():
    return _q("""
        SELECT nome_programma as programma_ue,
               COUNT(DISTINCT codice_fiscale) as n_ets,
               COUNT(*) as n_grant,
               ROUND(SUM(importo), 0) as importo_totale
        FROM _T_
        WHERE nome_programma IS NOT NULL AND nome_programma != ''
        GROUP BY nome_programma
        ORDER BY importo_totale DESC LIMIT 20
    """, CLEAN_FTS)


# -- Scheda ETS ---------------------------------------------------------

@st.cache_data(ttl=3600)
def scheda_ente_profilo(cf: str):
    """Profilo base da ets_unified."""
    return _q(f"SELECT * FROM _T_ WHERE codice_fiscale = '{cf}'", MART_ETS)

@st.cache_data(ttl=3600)
def scheda_ente_5xmille(cf: str):
    return _q(f"SELECT * FROM _T_ WHERE codice_fiscale = '{cf}'", MART_5XMILLE)

@st.cache_data(ttl=3600)
def scheda_ente_anac(cf: str):
    agg = _q(f"SELECT * FROM _T_ WHERE codice_fiscale = '{cf}'", MART_ANAC_AGG)
    par = _q(f"SELECT * FROM _T_ WHERE codice_fiscale = '{cf}'", MART_ANAC_PAR)
    return {"aggiudicazioni": agg, "partecipazioni": par}

@st.cache_data(ttl=3600)
def scheda_ente_rna(cf: str):
    return _q(f"SELECT * FROM _T_ WHERE codice_fiscale = '{cf}'", CLEAN_RNA)

@st.cache_data(ttl=3600)
def scheda_ente_pnrr(cf: str):
    return _q(f"SELECT * FROM _T_ WHERE codice_fiscale = '{cf}'", CLEAN_PNRR)

@st.cache_data(ttl=3600)
def scheda_ente_fts(cf: str):
    return _q(f"SELECT * FROM _T_ WHERE codice_fiscale = '{cf}'", CLEAN_FTS)

@st.cache_data(ttl=3600)
def scheda_ente_mef(cf: str):
    return _q(f"SELECT * FROM _T_ WHERE codice_fiscale = '{cf}'", CLEAN_MEF)

@st.cache_data(ttl=3600)
def scheda_ente_coesione(cf: str):
    return _q(f"SELECT * FROM _T_ WHERE codice_fiscale = '{cf}'", MART_COESIONE)


# -- Bandi --------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_bandi():
    all_bandi = []
    for src, fonte, key in [
        ("infobandi_bandi.json", "infobandi.csvnet.it", None),
        ("info_cooperazione_bandi.json", None, "bandi"),
    ]:
        p = ROOT / "data" / "bandi" / src
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else data.get(key, [])
        f = fonte or data.get("fonte", "")
        for b in items:
            all_bandi.append({
                "titolo": b.get("titolo", ""), "url": b.get("url", ""),
                "fonte": f, "ente": b.get("ente_erogatore") or b.get("donatore", ""),
                "scadenza": b.get("scadenza", ""), "tag": b.get("tag") or b.get("tags", []),
            })
    return all_bandi


# -- Coesione -----------------------------------------------------------

@st.cache_data(ttl=3600)
def top_ets_coesione(top_n: int = 20):
    return _q(f"""
        SELECT denominazione, comune, provincia, sezione,
               n_progetti_coesione, n_temi_coesione, fascia_coesione
        FROM _T_
        WHERE ha_progetti_coesione
        ORDER BY n_progetti_coesione DESC LIMIT {top_n}
    """, MART_COESIONE)


# -- Matching -----------------------------------------------------------

# Mapping tag bandi → temi OpenCoesione (normalizzazione)
TAG_TO_TEMA = {
    "lavoro": "Occupazione e lavoro",
    "occupazione": "Occupazione e lavoro",
    "formazione": "Istruzione e formazione",
    "educazione": "Istruzione e formazione",
    "scuole": "Istruzione e formazione",
    "inclusione sociale": "Inclusione sociale e salute",
    "inclusione": "Inclusione sociale e salute",
    "salute": "Inclusione sociale e salute",
    "disabilità": "Inclusione sociale e salute",
    "cultura": "Cultura e turismo",
    "sport": "Cultura e turismo",
    "giovani": "Occupazione e lavoro",
    "minori": "Inclusione sociale e salute",
    "donne": "Inclusione sociale e salute",
    "migranti": "Inclusione sociale e salute",
    "povertà": "Inclusione sociale e salute",
    "digitale": "Reti e servizi digitali",
    "ambiente": "Ambiente",
    "ricerca": "Ricerca e innovazione",
    "cooperazione allo sviluppo": "Competitività delle imprese",
}

def _normalize_tags(tags: list[str]) -> list[str]:
    """Normalizza i tag dei bandi in temi OpenCoesione."""
    temi = set()
    for tag in tags:
        tag_lower = tag.lower().strip()
        if tag_lower in TAG_TO_TEMA:
            temi.add(TAG_TO_TEMA[tag_lower])
        else:
            # Cerca match parziale
            for key, tema in TAG_TO_TEMA.items():
                if key in tag_lower or tag_lower in key:
                    temi.add(tema)
    return list(temi)

# -- Matching ---------------------------------------------------------------

# Mapping bando tags → colonne flag 5x1000 nel MART_ETS
TAG_TO_FLAG = {
    "sport": "ha_sport_in_denominazione",
    "ricerca": "ha_finanziamenti_ue",
    "cultura": "flag_beni_culturali",
    "ambiente": "flag_area_protetta",
}

# Sezioni RUNTS compatibili con bandi per tipo ente
SEZIONI_BANDI = {
    "cooperative": ["IMPRESE SOCIALI"],
    "volontariato": ["ORGANIZZAZIONI DI VOLONTARIATO"],
    "associazioni": ["ASSOCIAZIONI DI PROMOZIONE SOCIALE"],
}


def _bando_eligibility(bando: dict) -> str:
    """Ritorna WHERE clause SQL per idoneita del bando."""
    tags_lower = [t.lower() for t in bando.get("tag", [])]
    conditions = []

    # Filtro per sezione
    for key,sezioni in SEZIONI_BANDI.items():
        if any(key in t for t in tags_lower):
            lista = ",".join([f"'{s}'" for s in sezioni])
            conditions.append(f"e.sezione IN ({lista})")

    return " AND ".join(conditions) if conditions else "TRUE"


def _bando_theme_score(bando: dict) -> str:
    """Ritorna espressione SQL per il punteggio tematico."""
    tags_lower = [t.lower() for t in bando.get("tag", [])]
    parts = []

    for tag in tags_lower:
        for bando_key, flag_col in TAG_TO_FLAG.items():
            if bando_key in tag:
                # flag_ da mart 5xmille (prefisso f.), importo da ets (prefisso e.)
                if flag_col.startswith("flag_"):
                    parts.append(f"(CASE WHEN f.{flag_col} THEN 3 ELSE 0 END)")
                else:
                    parts.append(f"(CASE WHEN e.{flag_col} THEN 3 ELSE 0 END)")
                break

    # Bonus per 5x1000 alto (indica ente radicato nel territorio)
    parts.append("(CASE WHEN e.importo_5x1000_2025 > 50000 THEN 2 ELSE 0 END)")

    return " + ".join(parts) if parts else "0"


def _bando_capacity_score() -> str:
    """SQL expression per il punteggio di capacita."""
    return """
        + LEAST(COALESCE(a.n_appalti, 0) / 5, 3)
        + CASE WHEN e.ha_finanziamenti_ue THEN 2 ELSE 0 END
        + CASE WHEN COALESCE(a.ha_appalti_riservati, false) THEN 2 ELSE 0 END
        + LEAST(COALESCE(e.anni_5x1000, 0) / 2, 2)
    """


@st.cache_data(ttl=3600)
def match_bandi_ets(bando: dict, top_n: int = 20):
    """Trova ETS candidati per un bando.

    Funnel:
      1. Idoneita: filtra per sezione e territorio
      2. Pertinenza: score tematico (flag 5x1000, coesione)
      3. Ranking: capacita (appalti, grant UE, 5x1000 stabilita)
    """
    import pandas as pd

    eligibility = _bando_eligibility(bando)
    theme_score = _bando_theme_score(bando)
    capacity_score = _bando_capacity_score()

    return _q(f"""
        SELECT
            e.codice_fiscale,
            e.denominazione,
            e.sezione,
            e.comune,
            e.provincia,
            e.capacita_progettuale,
            COALESCE(a.n_appalti, 0) as n_appalti,
            COALESCE(a.ha_appalti_riservati, false) as ha_appalti_riservati,
            e.ha_finanziamenti_ue,
            e.anni_5x1000,
            ROUND(e.importo_5x1000_2025, 0) as importo_5x1000_2025,
            ({theme_score}) as tema_score,
            ({capacity_score}) as capacity_bonus,
            ({theme_score}) + ({capacity_score}) as score
        FROM read_parquet('{MART_ETS}') e
        LEFT JOIN read_parquet('{MART_ANAC_AGG}') a ON e.codice_fiscale = a.codice_fiscale
        LEFT JOIN read_parquet('{MART_5XMILLE}') f ON e.codice_fiscale = f.codice_fiscale
        WHERE ({eligibility})
          AND ({theme_score}) > 0
        ORDER BY score DESC
        LIMIT {top_n}
    """, MART_ETS)


def match_bandi_per_ets(cf: str, top_n: int = 10):
    """Trova bandi compatibili con un ETS dato il suo codice_fiscale."""
    # Profilo ETS
    profile = _q(f"SELECT * FROM _T_ WHERE codice_fiscale = '{cf}'", MART_ETS)
    if profile.empty:
        return []

    row = profile.iloc[0]

    # Flags 5x1000
    flags_5xm = _q(f"""
        SELECT flag_asd, flag_ricerca_scientifica, flag_ricerca_sanitaria,
               flag_comune, flag_beni_culturali, flag_area_protetta
        FROM _T_ WHERE codice_fiscale = '{cf}'
    """, MART_5XMILLE)

    et = {}
    if not flags_5xm.empty:
        et["flags"] = flags_5xm.iloc[0].to_dict()
    else:
        et["flags"] = {}

    et["sezione"] = row.get("sezione", "")
    et["regione"] = row.get("regione", "")
    et["provincia"] = row.get("provincia", "")
    et["capacita"] = row.get("capacita_progettuale", "sconosciuta")
    et["ha_5xmille"] = row.get("ha_5x1000", False)
    et["ha_appalti"] = row.get("ha_appalti_pubblici", False)
    et["ha_ue"] = row.get("ha_finanziamenti_ue", False)

    # Carica bandi
    bandi = load_bandi()
    if not bandi:
        return []

    scored = []
    for b in bandi:
        bando_tags = [t.lower() for t in b.get("tag", [])]
        score = 0

        # Theme match: bando tag → ETS flag
        for tag in bando_tags:
            for bando_key, flag_col in TAG_TO_FLAG.items():
                if bando_key in tag and et["flags"].get(flag_col):
                    score += 3
                    break

        # Capacity bonus
        if et["ha_ue"]:
            score += 2
        if et["ha_appalti"]:
            score += 1
        if et["ha_5xmille"]:
            score += 1

        if score > 0:
            scored.append({
                "titolo": b.get("titolo", ""),
                "url": b.get("url", ""),
                "ente": b.get("ente_erogatore", ""),
                "tags": b.get("tag", []),
                "scadenza": b.get("scadenza", ""),
                "score": score,
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]


# -- Territorio ---------------------------------------------------------


# -- Territorio ---------------------------------------------------------

@st.cache_data(ttl=3600)
def elenco_province():
    return _q("SELECT DISTINCT provincia FROM _T_ ORDER BY provincia", MART_ETS)

@st.cache_data(ttl=3600)
def elenco_regioni():
    return _q("SELECT DISTINCT regione FROM _T_ WHERE regione IS NOT NULL ORDER BY regione", MART_ETS)

@st.cache_data(ttl=3600)
def territorio_riepilogo(prov: str = None, reg: str = None):
    """Riepilogo territorio: ETS, sezioni, fonti."""
    where = []
    if prov:
        where.append(f"upper(provincia) = '{prov.upper()}'")
    elif reg:
        where.append(f"regione = '{reg}'")
    w = " WHERE " + " AND ".join(where) if where else ""
    
    return _q(f"""
        SELECT
            COUNT(*) as ets_totali,
            COUNT(CASE WHEN sezione = 'ORGANIZZAZIONI DI VOLONTARIATO' THEN 1 END) as odv,
            COUNT(CASE WHEN sezione = 'ASSOCIAZIONI DI PROMOZIONE SOCIALE' THEN 1 END) as aps,
            COUNT(CASE WHEN sezione = 'IMPRESE SOCIALI' THEN 1 END) as imprese_sociali,
            COUNT(CASE WHEN ha_5x1000 THEN 1 END) as con_5xmille,
            COUNT(CASE WHEN ha_finanziamenti_ue THEN 1 END) as con_ue,
            COUNT(CASE WHEN ha_aiuti_stato THEN 1 END) as con_rna,
            COUNT(CASE WHEN ha_progetti_pnrr THEN 1 END) as con_pnrr,
            COUNT(CASE WHEN ha_appalti_pubblici THEN 1 END) as con_anac,
            ROUND(AVG(CASE WHEN importo_5x1000_2025 > 0 THEN importo_5x1000_2025 END), 0) as media_5xmille,
            COUNT(CASE WHEN capacita_progettuale = 'alta' THEN 1 END) as capacita_alta,
            COUNT(CASE WHEN capacita_progettuale IN ('alta', 'medio-alta') THEN 1 END) as capacita_media_alta
        FROM _T_ {w}
    """, MART_ETS)

@st.cache_data(ttl=3600)
def territorio_fonti(prov: str = None, reg: str = None):
    """Distribuzione fonti per territorio."""
    where = []
    if prov:
        where.append(f"upper(provincia) = '{prov.upper()}'")
    elif reg:
        where.append(f"regione = '{reg}'")
    w = " WHERE " + " AND ".join(where) if where else ""
    
    return _q(f"""
        SELECT '5×1000' as fonte, COUNT(*) as enti FROM _T_ WHERE ha_5x1000 {('AND ' + ' AND '.join(where)) if where else ''}
        UNION ALL SELECT 'Grant UE', COUNT(*) FROM _T_ WHERE ha_finanziamenti_ue {('AND ' + ' AND '.join(where)) if where else ''}
        UNION ALL SELECT 'RNA', COUNT(*) FROM _T_ WHERE ha_aiuti_stato {('AND ' + ' AND '.join(where)) if where else ''}
        UNION ALL SELECT 'PNRR', COUNT(*) FROM _T_ WHERE ha_progetti_pnrr {('AND ' + ' AND '.join(where)) if where else ''}
        UNION ALL SELECT 'ANAC', COUNT(*) FROM _T_ WHERE ha_appalti_pubblici {('AND ' + ' AND '.join(where)) if where else ''}
        ORDER BY enti DESC
    """, MART_ETS)

@st.cache_data(ttl=3600)
def territorio_top_comuni(prov: str = None, reg: str = None, top_n: int = 15):
    """Top comuni per numero ETS."""
    where = []
    if prov:
        where.append(f"upper(provincia) = '{prov.upper()}'")
    elif reg:
        where.append(f"regione = '{reg}'")
    w = " WHERE " + " AND ".join(where) if where else ""
    
    return _q(f"""
        SELECT comune, provincia,
               COUNT(*) as ets_tot,
               COUNT(CASE WHEN ha_5x1000 THEN 1 END) as con_5xmille,
               COUNT(CASE WHEN ha_appalti_pubblici THEN 1 END) as con_anac,
               COUNT(CASE WHEN capacita_progettuale IN ('alta','medio-alta') THEN 1 END) as attivi
        FROM _T_ {w}
        GROUP BY comune, provincia
        ORDER BY ets_tot DESC
        LIMIT {top_n}
    """, MART_ETS)

@st.cache_data(ttl=3600)
def confronto_territorio(prov: str):
    """Confronto provincia vs nazionale."""
    return _q(f"""
        SELECT 'Provincia {prov}' as livello, COUNT(*) as totale,
               COUNT(CASE WHEN capacita_progettuale IN ('alta','medio-alta') THEN 1 END) as attivi,
               COUNT(CASE WHEN ha_5x1000 THEN 1 END) as con_5xmille,
               COUNT(CASE WHEN ha_appalti_pubblici THEN 1 END) as con_anac
        FROM _T_ WHERE upper(provincia) = '{prov.upper()}'
        UNION ALL
        SELECT 'Nazionale', COUNT(*),
               COUNT(CASE WHEN capacita_progettuale IN ('alta','medio-alta') THEN 1 END),
               COUNT(CASE WHEN ha_5x1000 THEN 1 END),
               COUNT(CASE WHEN ha_appalti_pubblici THEN 1 END)
        FROM _T_
    """, MART_ETS)


# -- ISTAT Censimento Non Profit 2023 ------------------------------------

@st.cache_data(ttl=3600)
def istat_2023_kpi():
    """KPI nazionali dal censimento 2023."""
    return _q("""
        SELECT
            SUM(CASE WHEN categoria_tipo = 'forma_giuridica' THEN istituzioni END) as istituzioni_totali,
            SUM(CASE WHEN categoria_tipo = 'forma_giuridica' THEN dipendenti END) as dipendenti_totali
        FROM _T_ WHERE livello = 'regione' AND regione = 'ITALIA'
    """, ISTAT_2023_CLEAN)

@st.cache_data(ttl=3600)
def istat_2023_regioni():
    """Istituzioni per regione (totale)."""
    return _q("SELECT * FROM _T_ ORDER BY istituzioni_totali DESC", ISTAT_2023_REGIONI)

@st.cache_data(ttl=3600)
def istat_2023_settori():
    """Istituzioni per settore e regione."""
    return _q("SELECT * FROM _T_ ORDER BY istituzioni DESC", ISTAT_2023_SETTORI)

@st.cache_data(ttl=3600)
def istat_2023_province():
    """Istituzioni per provincia."""
    return _q("SELECT * FROM _T_ ORDER BY istituzioni DESC", ISTAT_2023_PROVINCE)
