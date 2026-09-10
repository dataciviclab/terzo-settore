"""Data sources — usa load_mart_table / query_clean da lab_connectors."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
from lab_connectors.duckdb.queries import load_mart_table, query_clean
from lab_connectors.formatters import fmt_eur, fmt_num, fmt_pct  # noqa: F401

ROOT = Path(__file__).parent.parent
PREFIX = "terzo_settore/"
SLUG = "ets_unified"
YEARS = [2022, 2023, 2024, 2025, 2026]
_data_dir = ROOT / "out" / "data"
LOCAL_ROOT = str(_data_dir) if _data_dir.is_dir() and any(_data_dir.rglob("*.parquet")) else None


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart(table: str, year: int = 2026, slug: str = "") -> pd.DataFrame:
    return load_mart_table(slug or table, table, year, prefix=PREFIX, local_root=LOCAL_ROOT)


@st.cache_data(ttl=3600, show_spinner=False)
def query(sql: str, years: tuple[int, ...] = tuple(YEARS), slug: str = SLUG) -> pd.DataFrame:
    return query_clean(slug, sql, list(years), prefix=PREFIX, local_root=LOCAL_ROOT)


# -- Panoramica ---------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def kpi_nazionali():
    df = load_mart("runts_sezione", year=2026, slug="runts")
    return int(df["enti"].sum())

@st.cache_data(ttl=3600, show_spinner=False)
def kpi_con_5xmille():
    df = load_mart("ets_unified", year=2026)
    return int((df["importo_5x1000_2025"] > 0).sum())

@st.cache_data(ttl=3600, show_spinner=False)
def kpi_con_appalti():
    df = load_mart("ets_unified", year=2026)
    return int((df["numero_appalti"] > 0).sum())

@st.cache_data(ttl=3600, show_spinner=False)
def kpi_con_aiuti():
    df = load_mart("ets_unified", year=2026)
    return int((df["importo_aiuti_stato"] > 0).sum())

@st.cache_data(ttl=3600, show_spinner=False)
def n_ets_con_coesione():
    df = load_mart("ets_coesione", year=2026, slug="ets_opencoesione")
    return int(df["ha_progetti_coesione"].sum())

@st.cache_data(ttl=3600, show_spinner=False)
def fondi_per_fonte():
    rows = []
    for label, slug, table in [
        ("5×1000", "ets_5xmille", "ets_5xmille"),
        ("Grant UE", "ets_fts", "ets_fts"),
        ("RNA", "ets_rna", "ets_rna"),
        ("PNRR", "ets_pnrr", "ets_pnrr"),
        ("ANAC", "ets_anac", "ets_anac_aggiudicazioni"),
    ]:
        try:
            df = load_mart(table, year=2026, slug=slug)
            rows.append({"fonte": label, "enti": len(df), "importo": float(df["importo_totale"].sum() or 0)})
        except Exception:
            pass
    try:
        df = load_mart("ets_coesione", year=2026, slug="ets_opencoesione")
        rows.append({"fonte": "Coesione", "enti": int(df["ha_progetti_coesione"].sum()), "importo": 0})
    except Exception:
        pass
    return pd.DataFrame(rows)

@st.cache_data(ttl=3600, show_spinner=False)
def capacita_progettuale():
    df = load_mart("ets_unified", year=2026)
    return df.groupby("capacita_progettuale").size().reset_index(name="enti").sort_values("capacita_progettuale")

@st.cache_data(ttl=3600, show_spinner=False)
def top_ets_5xmille():
    df = load_mart("ets_unified", year=2026)
    return df[df["importo_5x1000_2025"] > 0][["denominazione", "comune", "provincia", "capacita_progettuale", "importo_5x1000_2025"]].sort_values("importo_5x1000_2025", ascending=False).head(15)


# -- Anagrafe -----------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def elenco_sezioni():
    df = load_mart("runts_sezione", year=2026, slug="runts")
    return df[["sezione"]].dropna().sort_values("sezione")


@st.cache_data(ttl=3600, show_spinner=False)
def anagrafe_join(comune=None, prov=None, sezione=None, search=None, limit=200):
    df_r = query("SELECT codice_fiscale, denominazione, sezione, comune, provincia, data_iscrizione FROM clean_input", years=[2026], slug="runts")
    df_e = load_mart("ets_unified", year=2026)[["codice_fiscale", "capacita_progettuale"]]
    df = df_r.merge(df_e, on="codice_fiscale", how="left")
    if comune:
        df = df[df["comune"].str.lower() == comune.lower()]
    if prov:
        df = df[df["provincia"].str.upper() == prov.upper()]
    if sezione:
        df = df[df["sezione"] == sezione]
    if search:
        s = search.lower()
        df = df[df["denominazione"].str.lower().str.contains(s, na=False) | df["codice_fiscale"].str.contains(s, na=False)]
    return df.sort_values("denominazione").head(limit)

@st.cache_data(ttl=3600, show_spinner=False)
def cerca_ente(q: str):
    df = load_mart("ets_unified", year=2026)
    s = q.lower()
    mask = df["denominazione"].str.lower().str.contains(s, na=False) | df["codice_fiscale"].str.contains(s, na=False)
    return df[mask][["codice_fiscale", "denominazione"]].head(20)


# -- 5x1000 -------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def cinque_per_anno():
    df = query("SELECT anno, COUNT(DISTINCT cf) as n_ets, ROUND(SUM(importo), 0) as importo_totale, ROUND(AVG(importo), 0) as importo_medio FROM clean_input WHERE fonte = '5x1000' GROUP BY anno ORDER BY anno", years=[2026])
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def cinque_per_tipologia():
    df = load_mart("ets_5xmille", year=2026)
    return pd.DataFrame([{
        "asd": int(df["flag_asd"].sum()),
        "ricerca_scientifica": int(df["flag_ricerca_scientifica"].sum()),
        "ricerca_sanitaria": int(df["flag_ricerca_sanitaria"].sum()),
        "beni_culturali": int(df["flag_beni_culturali"].sum()),
        "area_protetta": int(df["flag_area_protetta"].sum()),
        "comuni": int(df["flag_comune"].sum()),
        "totale": len(df),
    }])

@st.cache_data(ttl=3600, show_spinner=False)
def top_ets_5x1000():
    df = load_mart("ets_5xmille", year=2026)
    return df[["codice_fiscale", "denominazione", "comune", "provincia", "importo_totale", "anni", "flag_asd", "flag_ricerca_scientifica"]].sort_values("importo_totale", ascending=False).head(20)


# -- Trasparenza --------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def top_soggetti_concedenti(top_n=20):
    df = query("SELECT soggetto_concedente, COUNT(DISTINCT codice_fiscale) as n_beneficiari, COUNT(*) as n_concessioni, ROUND(SUM(importo), 0) as importo_totale FROM clean_input WHERE soggetto_concedente IS NOT NULL AND soggetto_concedente != '' GROUP BY soggetto_concedente ORDER BY importo_totale DESC", years=[2026], slug="ets_rna")
    return df.head(top_n)

@st.cache_data(ttl=3600, show_spinner=False)
def rna_per_procedimento():
    return query("SELECT COALESCE(procedimento, 'Non specificato') as procedimento, COUNT(DISTINCT codice_fiscale) as n_beneficiari, ROUND(SUM(importo), 0) as importo_totale FROM clean_input GROUP BY procedimento ORDER BY importo_totale DESC", years=[2026], slug="ets_rna")

@st.cache_data(ttl=3600, show_spinner=False)
def top_stazioni_appaltanti(top_n=20):
    return query("SELECT stazione_appaltante, COUNT(DISTINCT codice_fiscale) as n_ets, COUNT(*) as n_appalti, ROUND(SUM(importo), 0) as importo_totale FROM clean_input WHERE fonte = 'anac_aggiudicazione' AND stazione_appaltante IS NOT NULL AND stazione_appaltante != '' GROUP BY stazione_appaltante ORDER BY importo_totale DESC", years=[2026], slug="ets_anac").head(top_n)


# -- Programmi ----------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def pnrr_per_programma():
    return query("SELECT programma, descrizione_missione, COUNT(DISTINCT codice_fiscale) as n_ets, ROUND(SUM(importo), 0) as fin_totale FROM clean_input GROUP BY programma, descrizione_missione ORDER BY fin_totale DESC", years=[2026], slug="ets_pnrr")

@st.cache_data(ttl=3600, show_spinner=False)
def fts_per_programma():
    return query("SELECT nome_programma as programma_ue, COUNT(DISTINCT codice_fiscale) as n_ets, COUNT(*) as n_grant, ROUND(SUM(importo), 0) as importo_totale FROM clean_input WHERE nome_programma IS NOT NULL AND nome_programma != '' GROUP BY nome_programma ORDER BY importo_totale DESC", years=[2026], slug="ets_fts").head(20)


# -- Scheda ETS ---------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def scheda_ente_profilo(cf):
    df = load_mart("ets_unified", year=2026)
    r = df[df["codice_fiscale"] == cf]
    return r

@st.cache_data(ttl=3600, show_spinner=False)
def scheda_ente_5xmille(cf):
    df = load_mart("ets_5xmille", year=2026, slug="ets_5xmille")
    return df[df["codice_fiscale"] == cf]

@st.cache_data(ttl=3600, show_spinner=False)
def scheda_ente_anac(cf):
    agg = load_mart("ets_anac_aggiudicazioni", year=2026, slug="ets_anac")
    par = load_mart("ets_anac_partecipazioni", year=2026, slug="ets_anac")
    return {"aggiudicazioni": agg[agg["codice_fiscale"] == cf], "partecipazioni": par[par["codice_fiscale"] == cf]}

@st.cache_data(ttl=3600, show_spinner=False)
def scheda_ente_rna(cf):
    df = query("SELECT * FROM clean_input WHERE codice_fiscale = '" + cf.replace("'", "''") + "'", years=[2026], slug="ets_rna")
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def scheda_ente_pnrr(cf):
    df = query("SELECT * FROM clean_input WHERE codice_fiscale = '" + cf.replace("'", "''") + "'", years=[2026], slug="ets_pnrr")
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def scheda_ente_fts(cf):
    df = query("SELECT * FROM clean_input WHERE codice_fiscale = '" + cf.replace("'", "''") + "'", years=[2026], slug="ets_fts")
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def scheda_ente_mef(cf):
    df = query("SELECT * FROM clean_input WHERE codice_fiscale = '" + cf.replace("'", "''") + "'", years=[2026], slug="ets_mef")
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def scheda_ente_coesione(cf):
    df = load_mart("ets_coesione", year=2026, slug="ets_opencoesione")
    return df[df["codice_fiscale"] == cf]


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
    df = load_mart("ets_coesione", year=2026, slug="ets_opencoesione")
    return df[df["ha_progetti_coesione"]][["denominazione", "comune", "provincia", "sezione", "n_progetti_coesione", "n_temi_coesione", "fascia_coesione"]].sort_values("n_progetti_coesione", ascending=False).head(top_n)


# -- Matching -----------------------------------------------------------

TAG_TO_FLAG = {"sport": "ha_sport_in_denominazione", "ricerca": "ha_finanziamenti_ue", "cultura": "flag_beni_culturali", "ambiente": "flag_area_protetta"}
SEZIONI_BANDI = {"cooperative": ["IMPRESE SOCIALI"], "volontariato": ["ORGANIZZAZIONI DI VOLONTARIATO"], "associazioni": ["ASSOCIAZIONI DI PROMOZIONE SOCIALE"]}


def _bando_eligibility(bando):
    tags_lower = [t.lower() for t in bando.get("tag", [])]
    conditions = []
    for key, sezioni in SEZIONI_BANDI.items():
        if any(key in t for t in tags_lower):
            conditions.append(f"sezione IN ({','.join([repr(s) for s in sezioni])})")
    return conditions


def _compute_tema_score_vectorized(df, bando):
    """Vectorized replacement for df.apply(_bando_theme_match, axis=1)."""
    tags_lower = [t.lower() for t in bando.get("tag", [])]
    score = pd.Series(0, index=df.index)
    for tag in tags_lower:
        for bando_key, flag_col in TAG_TO_FLAG.items():
            if bando_key in tag and flag_col in df.columns:
                score = score + df[flag_col].fillna(False).astype(int) * 3
    if "importo_5x1000_2025" in df.columns:
        score = score + (df["importo_5x1000_2025"].fillna(0) > 50000).astype(int) * 2
    return score


@st.cache_data(ttl=3600, show_spinner=False)
def match_bandi_ets(bando, top_n=20):
    df_e = load_mart("ets_unified", year=2026)
    df_a = load_mart("ets_anac_aggiudicazioni", year=2026, slug="ets_anac")[["codice_fiscale", "n_appalti", "ha_appalti_riservati"]]
    df_f = load_mart("ets_5xmille", year=2026)[["codice_fiscale", "flag_asd", "flag_ricerca_scientifica", "flag_beni_culturali", "flag_area_protetta"]]
    df = df_e.merge(df_a, on="codice_fiscale", how="left").merge(df_f, on="codice_fiscale", how="left")

    eligibility = _bando_eligibility(bando)
    for cond in eligibility:
        df = df.query(cond)

    df["tema_score"] = _compute_tema_score_vectorized(df, bando)
    df = df[df["tema_score"] > 0]

    df["capacity_bonus"] = (
        df["n_appalti"].fillna(0).clip(upper=15) / 5
        + df["ha_finanziamenti_ue"].fillna(False).astype(int) * 2
        + df["ha_appalti_riservati"].fillna(False).astype(int) * 2
        + (df["anni_5x1000"].fillna(0) / 2).clip(upper=2)
    )
    df["score"] = df["tema_score"] + df["capacity_bonus"]
    return df.sort_values("score", ascending=False).head(top_n)


@st.cache_data(ttl=3600, show_spinner=False)
def match_bandi_per_ets(cf, top_n=10):
    df_e = load_mart("ets_unified", year=2026)
    row = df_e[df_e["codice_fiscale"] == cf]
    if row.empty:
        return []
    row = row.iloc[0]
    df_f = load_mart("ets_5xmille", year=2026, slug="ets_5xmille")
    flags = df_f[df_f["codice_fiscale"] == cf]
    et = {"flags": flags.iloc[0].to_dict() if not flags.empty else {},
          "ha_5xmille": row.get("ha_5x1000", False), "ha_appalti": row.get("ha_appalti_pubblici", False),
          "ha_ue": row.get("ha_finanziamenti_ue", False)}
    bandi = load_bandi()
    scored = []
    for b in bandi:
        score = 0
        for tag in [t.lower() for t in b.get("tag", [])]:
            for bk, fc in TAG_TO_FLAG.items():
                if bk in tag and et["flags"].get(fc):
                    score += 3
                    break
        if et["ha_ue"]: score += 2
        if et["ha_appalti"]: score += 1
        if et["ha_5xmille"]: score += 1
        if score > 0:
            scored.append({"titolo": b.get("titolo", ""), "url": b.get("url", ""), "ente": b.get("ente_erogatore", ""), "tags": b.get("tag", []), "scadenza": b.get("scadenza", ""), "score": score})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]


# -- Territorio ---------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def elenco_province():
    df = load_mart("ets_unified", year=2026)
    return df[["provincia"]].dropna().drop_duplicates().sort_values("provincia")

@st.cache_data(ttl=3600, show_spinner=False)
def elenco_regioni():
    df = load_mart("ets_unified", year=2026)
    return df[["regione"]].dropna().drop_duplicates().sort_values("regione")

@st.cache_data(ttl=3600, show_spinner=False)
def territorio_riepilogo(prov=None, reg=None):
    df = load_mart("ets_unified", year=2026)
    if prov:
        df = df[df["provincia"].str.upper() == prov.upper()]
    elif reg:
        df = df[df["regione"] == reg]
    return pd.DataFrame([{
        "ets_totali": len(df),
        "odv": int((df["sezione"] == "ORGANIZZAZIONI DI VOLONTARIATO").sum()),
        "aps": int((df["sezione"] == "ASSOCIAZIONI DI PROMOZIONE SOCIALE").sum()),
        "imprese_sociali": int((df["sezione"] == "IMPRESE SOCIALI").sum()),
        "con_5xmille": int(df["ha_5x1000"].sum()),
        "con_ue": int(df["ha_finanziamenti_ue"].sum()),
        "con_rna": int(df["ha_aiuti_stato"].sum()),
        "con_pnrr": int(df["ha_progetti_pnrr"].sum()),
        "con_anac": int(df["ha_appalti_pubblici"].sum()),
        "media_5xmille": float(df.loc[df["importo_5x1000_2025"] > 0, "importo_5x1000_2025"].mean() or 0),
        "capacita_alta": int((df["capacita_progettuale"] == "alta").sum()),
        "capacita_media_alta": int(df["capacita_progettuale"].isin(["alta", "medio-alta"]).sum()),
    }])

@st.cache_data(ttl=3600, show_spinner=False)
def territorio_fonti(prov=None, reg=None):
    df = load_mart("ets_unified", year=2026)
    if prov:
        df = df[df["provincia"].str.upper() == prov.upper()]
    elif reg:
        df = df[df["regione"] == reg]
    return pd.DataFrame([
        {"fonte": "5×1000", "enti": int(df["ha_5x1000"].sum())},
        {"fonte": "Grant UE", "enti": int(df["ha_finanziamenti_ue"].sum())},
        {"fonte": "RNA", "enti": int(df["ha_aiuti_stato"].sum())},
        {"fonte": "PNRR", "enti": int(df["ha_progetti_pnrr"].sum())},
        {"fonte": "ANAC", "enti": int(df["ha_appalti_pubblici"].sum())},
    ]).sort_values("enti", ascending=False)

@st.cache_data(ttl=3600, show_spinner=False)
def territorio_top_comuni(prov=None, reg=None, top_n=15):
    df = load_mart("ets_unified", year=2026)
    if prov:
        df = df[df["provincia"].str.upper() == prov.upper()]
    elif reg:
        df = df[df["regione"] == reg]
    df["_attivo"] = df["capacita_progettuale"].isin(["alta", "medio-alta"]).astype(int)
    return df.groupby(["comune", "provincia"], sort=False).agg(
        ets_tot=("codice_fiscale", "count"),
        con_5xmille=("ha_5x1000", "sum"),
        con_anac=("ha_appalti_pubblici", "sum"),
        attivi=("_attivo", "sum"),
    ).reset_index().sort_values("ets_tot", ascending=False).head(top_n)

@st.cache_data(ttl=3600, show_spinner=False)
def confronto_territorio(prov):
    df = load_mart("ets_unified", year=2026)
    prov_df = df[df["provincia"].str.upper() == prov.upper()]
    return pd.DataFrame([
        {"livello": f"Provincia {prov}", "totale": len(prov_df), "attivi": int(prov_df["capacita_progettuale"].isin(["alta", "medio-alta"]).sum()), "con_5xmille": int(prov_df["ha_5x1000"].sum()), "con_anac": int(prov_df["ha_appalti_pubblici"].sum())},
        {"livello": "Nazionale", "totale": len(df), "attivi": int(df["capacita_progettuale"].isin(["alta", "medio-alta"]).sum()), "con_5xmille": int(df["ha_5x1000"].sum()), "con_anac": int(df["ha_appalti_pubblici"].sum())},
    ])


# -- ISTAT Censimento Non Profit 2023 ------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def istat_2023_kpi():
    df = query("SELECT SUM(CASE WHEN categoria_tipo = 'forma_giuridica' THEN istituzioni END) as istituzioni_totali, SUM(CASE WHEN categoria_tipo = 'forma_giuridica' THEN dipendenti END) as dipendenti_totali FROM clean_input WHERE livello = 'regione' AND regione = 'ITALIA'", years=[2023], slug="istat_non_profit_2023")
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def istat_2023_regioni():
    return load_mart("nonprofit_by_regione", year=2023, slug="istat_non_profit_2023").sort_values("istituzioni_totali", ascending=False)

@st.cache_data(ttl=3600, show_spinner=False)
def istat_2023_settori():
    return load_mart("nonprofit_by_settore", year=2023, slug="istat_non_profit_2023").sort_values("istituzioni", ascending=False)

@st.cache_data(ttl=3600, show_spinner=False)
def istat_2023_province():
    return load_mart("nonprofit_by_provincia", year=2023, slug="istat_non_profit_2023").sort_values("istituzioni", ascending=False)
