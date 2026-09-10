"""Data sources — legge dai compose via lab_connectors (path resolution automatica)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from lab_connectors.duckdb import safe_connect
from lab_connectors.duckdb.queries import load_mart_table as _load_mart
from lab_connectors.formatters import fmt_eur, fmt_num, fmt_pct
from lab_connectors.gcs.paths import https_url

ROOT = Path(__file__).parent.parent
PREFIX = "terzo_settore/"


def _url(layer: str, slug: str, table: str = "", year: int = 2026) -> str:
    """Risolvi URL parquet: GCS o locale (auto-detect out/data/)."""
    if layer == "mart":
        return https_url("mart", "mart_parquet", slug=slug, year=str(year), table=table, prefix=PREFIX)
    elif layer == "clean":
        return https_url("clean", "clean_parquet", slug=slug, year=year, prefix=PREFIX)
    raise ValueError(f"Layer sconosciuto: {layer}")


def _q(sql: str, url: str) -> pd.DataFrame:
    """Esegui SQL su un parquet (GCS o locale)."""
    with safe_connect() as con:
        return con.sql(sql.replace("_T_", f"read_parquet('{url}')")).df()


def load_mart(table: str, slug: str = "ets_unified", year: int = 2026) -> pd.DataFrame:
    """Carica un singolo mart table."""
    return _load_mart(slug, table, year, prefix=PREFIX)


# -- Panoramica ---------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def kpi_nazionali():
    url = _url("clean", "runts", year=2026)
    r = _q("SELECT COUNT(*) as totale FROM _T_", url)
    return int(r.iloc[0]["totale"])

@st.cache_data(ttl=3600, show_spinner=False)
def kpi_con_5xmille():
    url = _url("mart", "ets_unified", "ets_unified", 2026)
    r = _q("SELECT COUNT(*) as totale FROM _T_ WHERE importo_5x1000_2025 > 0", url)
    return int(r.iloc[0]["totale"])

@st.cache_data(ttl=3600, show_spinner=False)
def kpi_con_appalti():
    url = _url("mart", "ets_unified", "ets_unified", 2026)
    r = _q("SELECT COUNT(*) as totale FROM _T_ WHERE numero_appalti > 0", url)
    return int(r.iloc[0]["totale"])

@st.cache_data(ttl=3600, show_spinner=False)
def kpi_con_aiuti():
    url = _url("mart", "ets_unified", "ets_unified", 2026)
    r = _q("SELECT COUNT(*) as totale FROM _T_ WHERE importo_aiuti_stato > 0", url)
    return int(r.iloc[0]["totale"])

@st.cache_data(ttl=3600, show_spinner=False)
def n_ets_con_coesione():
    url = _url("mart", "ets_opencoesione", "ets_coesione", 2026)
    r = _q("SELECT COUNT(*) as totale FROM _T_ WHERE ha_progetti_coesione", url)
    return int(r.iloc[0]["totale"])

@st.cache_data(ttl=3600, show_spinner=False)
def fondi_per_fonte():
    rows = []
    for label, slug, table, imp_col in [
        ("5×1000", "ets_5xmille", "ets_5xmille", "importo_totale"),
        ("Grant UE", "ets_fts", "ets_fts", "importo_totale"),
        ("RNA", "ets_rna", "ets_rna", "importo_totale"),
        ("PNRR", "ets_pnrr", "ets_pnrr", "importo_totale"),
        ("ANAC", "ets_anac", "ets_anac_aggiudicazioni", "importo_totale"),
    ]:
        try:
            url = _url("mart", slug, table, 2026)
            df = _q(f"SELECT COUNT(*) as enti, ROUND(SUM({imp_col}),0) as importo FROM _T_", url)
            rows.append({"fonte": label, "enti": int(df.iloc[0]["enti"]), "importo": float(df.iloc[0]["importo"] or 0)})
        except Exception:
            pass
    try:
        url = _url("mart", "ets_opencoesione", "ets_coesione", 2026)
        df = _q("SELECT COUNT(*) as enti FROM _T_ WHERE ha_progetti_coesione", url)
        rows.append({"fonte": "Coesione", "enti": int(df.iloc[0]["enti"]), "importo": 0})
    except Exception:
        pass
    return pd.DataFrame(rows)

@st.cache_data(ttl=3600, show_spinner=False)
def capacita_progettuale():
    url = _url("mart", "ets_unified", "ets_unified", 2026)
    return _q("SELECT capacita_progettuale as livello, COUNT(*) as enti FROM _T_ GROUP BY livello ORDER BY livello", url)

@st.cache_data(ttl=3600, show_spinner=False)
def top_ets_5xmille():
    url = _url("mart", "ets_unified", "ets_unified", 2026)
    return _q("SELECT denominazione, comune, provincia, capacita_progettuale, ROUND(importo_5x1000_2025, 0) as importo_5x1000_2025 FROM _T_ WHERE importo_5x1000_2025 > 0 ORDER BY importo_5x1000_2025 DESC LIMIT 15", url)


# -- Anagrafe -----------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def anagrafe_enti(comune=None, prov=None, sezione=None, search=None, limit=200):
    where = []
    if comune:
        where.append(f"lower(comune) = '{comune.lower().replace(chr(39),'')}'")
    if prov:
        where.append(f"upper(provincia) = '{prov.upper()}'")
    if sezione:
        where.append(f"sezione = '{sezione}'")
    if search:
        s = search.replace("'", "''")
        where.append(f"(denominazione LIKE '%{s}%' OR codice_fiscale LIKE '%{s}%'")
    w = " WHERE " + " AND ".join(where) if where else ""
    url = _url("clean", "runts", year=2026)
    return _q(f"SELECT codice_fiscale, denominazione, sezione, comune, provincia, data_iscrizione FROM _T_ {w} ORDER BY denominazione LIMIT {limit}", url)

@st.cache_data(ttl=3600, show_spinner=False)
def elenco_sezioni():
    url = _url("clean", "runts", year=2026)
    return _q("SELECT DISTINCT sezione FROM _T_ ORDER BY sezione", url)


@st.cache_data(ttl=3600, show_spinner=False)
def anagrafe_join(comune=None, prov=None, sezione=None, search=None, limit=200):
    """Anagrafe ETS con capacita progettuale (JOIN RUNTS + mart ets_unified)."""
    where = []
    if comune:
        where.append(f"lower(r.comune) = '{comune.lower().replace(chr(39),'')}'")
    if prov:
        where.append(f"upper(r.provincia) = '{prov.upper()}'")
    if sezione:
        where.append(f"r.sezione = '{sezione}'")
    if search:
        s = search.replace("'", "''")
        where.append(f"(r.denominazione LIKE '%{s}%' OR r.codice_fiscale LIKE '%{s}%')")
    w = " WHERE " + " AND ".join(where) if where else ""
    url_r = _url("clean", "runts", year=2026)
    url_e = _url("mart", "ets_unified", "ets_unified", 2026)
    return _q(f"""
        SELECT r.codice_fiscale, r.denominazione, r.sezione, r.comune, r.provincia,
               r.data_iscrizione, m.capacita_progettuale
        FROM read_parquet('{url_r}') r
        LEFT JOIN read_parquet('{url_e}') m ON r.codice_fiscale = m.codice_fiscale
        {w} ORDER BY r.denominazione LIMIT {limit}
    """, url_r)


# -- 5x1000 -------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def cinque_per_anno():
    url = _url("clean", "ets_unified", year=2026)
    return _q("SELECT anno, COUNT(DISTINCT cf) as n_ets, ROUND(SUM(importo), 0) as importo_totale, ROUND(AVG(importo), 0) as importo_medio FROM _T_ WHERE fonte = '5x1000' GROUP BY anno ORDER BY anno", url)

@st.cache_data(ttl=3600, show_spinner=False)
def cinque_per_tipologia():
    url = _url("mart", "ets_5xmille", "ets_5xmille", 2026)
    return _q("SELECT SUM(CASE WHEN flag_asd THEN 1 ELSE 0 END) as asd, SUM(CASE WHEN flag_ricerca_scientifica THEN 1 ELSE 0 END) as ricerca_scientifica, SUM(CASE WHEN flag_ricerca_sanitaria THEN 1 ELSE 0 END) as ricerca_sanitaria, SUM(CASE WHEN flag_beni_culturali THEN 1 ELSE 0 END) as beni_culturali, SUM(CASE WHEN flag_area_protetta THEN 1 ELSE 0 END) as area_protetta, SUM(CASE WHEN flag_comune THEN 1 ELSE 0 END) as comuni, COUNT(*) as totale FROM _T_", url)

@st.cache_data(ttl=3600, show_spinner=False)
def top_ets_5x1000():
    url = _url("mart", "ets_5xmille", "ets_5xmille", 2026)
    return _q("SELECT codice_fiscale as cf, denominazione, comune, provincia, importo_totale, anni, flag_asd, flag_ricerca_scientifica FROM _T_ ORDER BY importo_totale DESC LIMIT 20", url)


# -- Trasparenza --------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def top_soggetti_concedenti(top_n=20):
    url = _url("clean", "ets_rna", year=2026)
    return _q(f"SELECT soggetto_concedente, COUNT(DISTINCT codice_fiscale) as n_beneficiari, COUNT(*) as n_concessioni, ROUND(SUM(importo), 0) as importo_totale FROM _T_ WHERE soggetto_concedente IS NOT NULL AND soggetto_concedente != '' GROUP BY soggetto_concedente ORDER BY importo_totale DESC LIMIT {top_n}", url)

@st.cache_data(ttl=3600, show_spinner=False)
def rna_per_procedimento():
    url = _url("clean", "ets_rna", year=2026)
    return _q("SELECT COALESCE(procedimento, 'Non specificato') as procedimento, COUNT(DISTINCT codice_fiscale) as n_beneficiari, ROUND(SUM(importo), 0) as importo_totale FROM _T_ GROUP BY procedimento ORDER BY importo_totale DESC", url)

@st.cache_data(ttl=3600, show_spinner=False)
def top_stazioni_appaltanti(top_n=20):
    url = _url("clean", "ets_anac", year=2026)
    return _q(f"SELECT stazione_appaltante, COUNT(DISTINCT codice_fiscale) as n_ets, COUNT(*) as n_appalti, ROUND(SUM(importo), 0) as importo_totale FROM _T_ WHERE fonte = 'anac_aggiudicazione' AND stazione_appaltante IS NOT NULL AND stazione_appaltante != '' GROUP BY stazione_appaltante ORDER BY importo_totale DESC LIMIT {top_n}", url)


# -- Programmi ----------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def pnrr_per_programma():
    url = _url("clean", "ets_pnrr", year=2026)
    return _q("SELECT programma, descrizione_missione, COUNT(DISTINCT codice_fiscale) as n_ets, ROUND(SUM(importo), 0) as fin_totale FROM _T_ GROUP BY programma, descrizione_missione ORDER BY fin_totale DESC", url)

@st.cache_data(ttl=3600, show_spinner=False)
def fts_per_programma():
    url = _url("clean", "ets_fts", year=2026)
    return _q("SELECT nome_programma as programma_ue, COUNT(DISTINCT codice_fiscale) as n_ets, COUNT(*) as n_grant, ROUND(SUM(importo), 0) as importo_totale FROM _T_ WHERE nome_programma IS NOT NULL AND nome_programma != '' GROUP BY nome_programma ORDER BY importo_totale DESC LIMIT 20", url)


# -- Scheda ETS ---------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def scheda_ente_profilo(cf):
    url = _url("mart", "ets_unified", "ets_unified", 2026)
    return _q(f"SELECT * FROM _T_ WHERE codice_fiscale = '{cf}'", url)

@st.cache_data(ttl=3600, show_spinner=False)
def scheda_ente_5xmille(cf):
    url = _url("mart", "ets_5xmille", "ets_5xmille", 2026)
    return _q(f"SELECT * FROM _T_ WHERE codice_fiscale = '{cf}'", url)

@st.cache_data(ttl=3600, show_spinner=False)
def scheda_ente_anac(cf):
    url_agg = _url("mart", "ets_anac", "ets_anac_aggiudicazioni", 2026)
    url_par = _url("mart", "ets_anac", "ets_anac_partecipazioni", 2026)
    return {"aggiudicazioni": _q(f"SELECT * FROM _T_ WHERE codice_fiscale = '{cf}'", url_agg),
            "partecipazioni": _q(f"SELECT * FROM _T_ WHERE codice_fiscale = '{cf}'", url_par)}

@st.cache_data(ttl=3600, show_spinner=False)
def scheda_ente_rna(cf):
    url = _url("clean", "ets_rna", year=2026)
    return _q(f"SELECT * FROM _T_ WHERE codice_fiscale = '{cf}'", url)

@st.cache_data(ttl=3600, show_spinner=False)
def scheda_ente_pnrr(cf):
    url = _url("clean", "ets_pnrr", year=2026)
    return _q(f"SELECT * FROM _T_ WHERE codice_fiscale = '{cf}'", url)

@st.cache_data(ttl=3600, show_spinner=False)
def scheda_ente_fts(cf):
    url = _url("clean", "ets_fts", year=2026)
    return _q(f"SELECT * FROM _T_ WHERE codice_fiscale = '{cf}'", url)

@st.cache_data(ttl=3600, show_spinner=False)
def scheda_ente_mef(cf):
    url = _url("clean", "ets_mef", year=2026)
    return _q(f"SELECT * FROM _T_ WHERE codice_fiscale = '{cf}'", url)

@st.cache_data(ttl=3600, show_spinner=False)
def scheda_ente_coesione(cf):
    url = _url("mart", "ets_opencoesione", "ets_coesione", 2026)
    return _q(f"SELECT * FROM _T_ WHERE codice_fiscale = '{cf}'", url)


@st.cache_data(ttl=3600, show_spinner=False)
def cerca_ente(query: str):
    """Cerca ente per CF o denominazione nel mart ets_unified."""
    safe = query.replace("'", "''")
    url = _url("mart", "ets_unified", "ets_unified", 2026)
    return _q(f"SELECT codice_fiscale, denominazione FROM _T_ WHERE codice_fiscale LIKE '%{safe}%' OR denominazione LIKE '%{safe}%' LIMIT 20", url)


# -- Bandi --------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
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

@st.cache_data(ttl=3600, show_spinner=False)
def top_ets_coesione(top_n=20):
    url = _url("mart", "ets_opencoesione", "ets_coesione", 2026)
    return _q(f"SELECT denominazione, comune, provincia, sezione, n_progetti_coesione, n_temi_coesione, fascia_coesione FROM _T_ WHERE ha_progetti_coesione ORDER BY n_progetti_coesione DESC LIMIT {top_n}", url)


# -- Matching -----------------------------------------------------------

TAG_TO_FLAG = {
    "sport": "ha_sport_in_denominazione",
    "ricerca": "ha_finanziamenti_ue",
    "cultura": "flag_beni_culturali",
    "ambiente": "flag_area_protetta",
}

SEZIONI_BANDI = {
    "cooperative": ["IMPRESE SOCIALI"],
    "volontariato": ["ORGANIZZAZIONI DI VOLONTARIATO"],
    "associazioni": ["ASSOCIAZIONI DI PROMOZIONE SOCIALE"],
}


def _bando_eligibility(bando: dict) -> str:
    tags_lower = [t.lower() for t in bando.get("tag", [])]
    conditions = []
    for key, sezioni in SEZIONI_BANDI.items():
        if any(key in t for t in tags_lower):
            lista = ",".join([f"'{s}'" for s in sezioni])
            conditions.append(f"e.sezione IN ({lista})")
    return " AND ".join(conditions) if conditions else "TRUE"


def _bando_theme_score(bando: dict) -> str:
    tags_lower = [t.lower() for t in bando.get("tag", [])]
    parts = []
    for tag in tags_lower:
        for bando_key, flag_col in TAG_TO_FLAG.items():
            if bando_key in tag:
                prefix = "f." if flag_col.startswith("flag_") else "e."
                parts.append(f"(CASE WHEN {prefix}{flag_col} THEN 3 ELSE 0 END)")
                break
    parts.append("(CASE WHEN e.importo_5x1000_2025 > 50000 THEN 2 ELSE 0 END)")
    return " + ".join(parts) if parts else "0"


def _bando_capacity_score() -> str:
    return """
        + LEAST(COALESCE(a.n_appalti, 0) / 5, 3)
        + CASE WHEN e.ha_finanziamenti_ue THEN 2 ELSE 0 END
        + CASE WHEN COALESCE(a.ha_appalti_riservati, false) THEN 2 ELSE 0 END
        + LEAST(COALESCE(e.anni_5x1000, 0) / 2, 2)
    """


@st.cache_data(ttl=3600, show_spinner=False)
def match_bandi_ets(bando: dict, top_n: int = 20):
    eligibility = _bando_eligibility(bando)
    theme_score = _bando_theme_score(bando)
    capacity_score = _bando_capacity_score()
    url_e = _url("mart", "ets_unified", "ets_unified", 2026)
    url_a = _url("mart", "ets_anac", "ets_anac_aggiudicazioni", 2026)
    url_f = _url("mart", "ets_5xmille", "ets_5xmille", 2026)
    return _q(f"""
        SELECT e.codice_fiscale, e.denominazione, e.sezione, e.comune, e.provincia,
               e.capacita_progettuale, COALESCE(a.n_appalti, 0) as n_appalti,
               COALESCE(a.ha_appalti_riservati, false) as ha_appalti_riservati,
               e.ha_finanziamenti_ue, e.anni_5x1000, ROUND(e.importo_5x1000_2025, 0) as importo_5x1000_2025,
               ({theme_score}) as tema_score, ({capacity_score}) as capacity_bonus,
               ({theme_score}) + ({capacity_score}) as score
        FROM read_parquet('{url_e}') e
        LEFT JOIN read_parquet('{url_a}') a ON e.codice_fiscale = a.codice_fiscale
        LEFT JOIN read_parquet('{url_f}') f ON e.codice_fiscale = f.codice_fiscale
        WHERE ({eligibility}) AND ({theme_score}) > 0
        ORDER BY score DESC LIMIT {top_n}
    """, url_e)


def match_bandi_per_ets(cf: str, top_n: int = 10):
    url_e = _url("mart", "ets_unified", "ets_unified", 2026)
    url_f = _url("mart", "ets_5xmille", "ets_5xmille", 2026)
    profile = _q(f"SELECT * FROM _T_ WHERE codice_fiscale = '{cf}'", url_e)
    if profile.empty:
        return []
    row = profile.iloc[0]
    flags_5xm = _q(f"SELECT flag_asd, flag_ricerca_scientifica, flag_ricerca_sanitaria, flag_comune, flag_beni_culturali, flag_area_protetta FROM _T_ WHERE codice_fiscale = '{cf}'", url_f)
    et = {"flags": flags_5xm.iloc[0].to_dict() if not flags_5xm.empty else {},
          "sezione": row.get("sezione", ""), "ha_5xmille": row.get("ha_5x1000", False),
          "ha_appalti": row.get("ha_appalti_pubblici", False), "ha_ue": row.get("ha_finanziamenti_ue", False)}
    bandi = load_bandi()
    if not bandi:
        return []
    scored = []
    for b in bandi:
        bando_tags = [t.lower() for t in b.get("tag", [])]
        score = 0
        for tag in bando_tags:
            for bando_key, flag_col in TAG_TO_FLAG.items():
                if bando_key in tag and et["flags"].get(flag_col):
                    score += 3
                    break
        if et["ha_ue"]: score += 2
        if et["ha_appalti"]: score += 1
        if et["ha_5xmille"]: score += 1
        if score > 0:
            scored.append({"titolo": b.get("titolo", ""), "url": b.get("url", ""),
                           "ente": b.get("ente_erogatore", ""), "tags": b.get("tag", []),
                           "scadenza": b.get("scadenza", ""), "score": score})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]


# -- Territorio ---------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def elenco_province():
    url = _url("mart", "ets_unified", "ets_unified", 2026)
    return _q("SELECT DISTINCT provincia FROM _T_ ORDER BY provincia", url)

@st.cache_data(ttl=3600, show_spinner=False)
def elenco_regioni():
    url = _url("mart", "ets_unified", "ets_unified", 2026)
    return _q("SELECT DISTINCT regione FROM _T_ WHERE regione IS NOT NULL ORDER BY regione", url)

@st.cache_data(ttl=3600, show_spinner=False)
def territorio_riepilogo(prov=None, reg=None):
    where = []
    if prov: where.append(f"upper(provincia) = '{prov.upper()}'")
    elif reg: where.append(f"regione = '{reg}'")
    w = " WHERE " + " AND ".join(where) if where else ""
    url = _url("mart", "ets_unified", "ets_unified", 2026)
    return _q(f"SELECT COUNT(*) as ets_totali, COUNT(CASE WHEN sezione = 'ORGANIZZAZIONI DI VOLONTARIATO' THEN 1 END) as odv, COUNT(CASE WHEN sezione = 'ASSOCIAZIONI DI PROMOZIONE SOCIALE' THEN 1 END) as aps, COUNT(CASE WHEN sezione = 'IMPRESE SOCIALI' THEN 1 END) as imprese_sociali, COUNT(CASE WHEN ha_5x1000 THEN 1 END) as con_5xmille, COUNT(CASE WHEN ha_finanziamenti_ue THEN 1 END) as con_ue, COUNT(CASE WHEN ha_aiuti_stato THEN 1 END) as con_rna, COUNT(CASE WHEN ha_progetti_pnrr THEN 1 END) as con_pnrr, COUNT(CASE WHEN ha_appalti_pubblici THEN 1 END) as con_anac, ROUND(AVG(CASE WHEN importo_5x1000_2025 > 0 THEN importo_5x1000_2025 END), 0) as media_5xmille, COUNT(CASE WHEN capacita_progettuale = 'alta' THEN 1 END) as capacita_alta, COUNT(CASE WHEN capacita_progettuale IN ('alta', 'medio-alta') THEN 1 END) as capacita_media_alta FROM _T_ {w}", url)

@st.cache_data(ttl=3600, show_spinner=False)
def territorio_fonti(prov=None, reg=None):
    where = []
    if prov: where.append(f"upper(provincia) = '{prov.upper()}'")
    elif reg: where.append(f"regione = '{reg}'")
    cond = (" AND " + " AND ".join(where)) if where else ""
    url = _url("mart", "ets_unified", "ets_unified", 2026)
    return _q(f"SELECT '5×1000' as fonte, COUNT(*) as enti FROM _T_ WHERE ha_5x1000 {cond} UNION ALL SELECT 'Grant UE', COUNT(*) FROM _T_ WHERE ha_finanziamenti_ue {cond} UNION ALL SELECT 'RNA', COUNT(*) FROM _T_ WHERE ha_aiuti_stato {cond} UNION ALL SELECT 'PNRR', COUNT(*) FROM _T_ WHERE ha_progetti_pnrr {cond} UNION ALL SELECT 'ANAC', COUNT(*) FROM _T_ WHERE ha_appalti_pubblici {cond} ORDER BY enti DESC", url)

@st.cache_data(ttl=3600, show_spinner=False)
def territorio_top_comuni(prov=None, reg=None, top_n=15):
    where = []
    if prov: where.append(f"upper(provincia) = '{prov.upper()}'")
    elif reg: where.append(f"regione = '{reg}'")
    w = " WHERE " + " AND ".join(where) if where else ""
    url = _url("mart", "ets_unified", "ets_unified", 2026)
    return _q(f"SELECT comune, provincia, COUNT(*) as ets_tot, COUNT(CASE WHEN ha_5x1000 THEN 1 END) as con_5xmille, COUNT(CASE WHEN ha_appalti_pubblici THEN 1 END) as con_anac, COUNT(CASE WHEN capacita_progettuale IN ('alta','medio-alta') THEN 1 END) as attivi FROM _T_ {w} GROUP BY comune, provincia ORDER BY ets_tot DESC LIMIT {top_n}", url)

@st.cache_data(ttl=3600, show_spinner=False)
def confronto_territorio(prov):
    url = _url("mart", "ets_unified", "ets_unified", 2026)
    return _q(f"SELECT 'Provincia {prov}' as livello, COUNT(*) as totale, COUNT(CASE WHEN capacita_progettuale IN ('alta','medio-alta') THEN 1 END) as attivi, COUNT(CASE WHEN ha_5x1000 THEN 1 END) as con_5xmille, COUNT(CASE WHEN ha_appalti_pubblici THEN 1 END) as con_anac FROM _T_ WHERE upper(provincia) = '{prov.upper()}' UNION ALL SELECT 'Nazionale', COUNT(*), COUNT(CASE WHEN capacita_progettuale IN ('alta','medio-alta') THEN 1 END), COUNT(CASE WHEN ha_5x1000 THEN 1 END), COUNT(CASE WHEN ha_appalti_pubblici THEN 1 END) FROM _T_", url)


# -- ISTAT Censimento Non Profit 2023 ------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def istat_2023_kpi():
    url = _url("clean", "istat_non_profit_2023", year=2023)
    return _q("SELECT SUM(CASE WHEN categoria_tipo = 'forma_giuridica' THEN istituzioni END) as istituzioni_totali, SUM(CASE WHEN categoria_tipo = 'forma_giuridica' THEN dipendenti END) as dipendenti_totali FROM _T_ WHERE livello = 'regione' AND regione = 'ITALIA'", url)

@st.cache_data(ttl=3600, show_spinner=False)
def istat_2023_regioni():
    url = _url("mart", "istat_non_profit_2023", "nonprofit_by_regione", 2023)
    return _q("SELECT * FROM _T_ ORDER BY istituzioni_totali DESC", url)

@st.cache_data(ttl=3600, show_spinner=False)
def istat_2023_settori():
    url = _url("mart", "istat_non_profit_2023", "nonprofit_by_settore", 2023)
    return _q("SELECT * FROM _T_ ORDER BY istituzioni DESC", url)

@st.cache_data(ttl=3600, show_spinner=False)
def istat_2023_province():
    url = _url("mart", "istat_non_profit_2023", "nonprofit_by_provincia", 2023)
    return _q("SELECT * FROM _T_ ORDER BY istituzioni DESC", url)
