#!/usr/bin/env python3
"""Analytics — calcolo puro delle viste per i report (nessuna formattazione).

Ogni funzione ritorna un dict/lista JSON-serializzabile con i dati grezzi;
il rendering (markdown/json) vive in match/reports/render/.
"""

from datetime import datetime
from hashlib import md5
from pathlib import Path

import duckdb
import pandas as pd

from config import gcs_path
from lib.format import fmt_match_reason
from match.funnel import match_bando_funnel
from match.pipeline import load_bandi

ROOT = Path(__file__).resolve().parents[2]
COMUNI_ETS_PATH = ROOT / "data" / "comuni_ets.parquet"
UNIFIED_COMUNI_URL = gcs_path("unified_comuni", 2026)
INPS_RDC_URL = gcs_path("inps_rdc_pdc", 2020)

_bandi_cache = None


def _bandi():
    global _bandi_cache
    if _bandi_cache is None:
        _bandi_cache = load_bandi()
    return _bandi_cache


# ── Gap territoriali ────────────────────────────────────────────────

def gap_territoriale(con, limite=10, provincia=None):
    """Comuni con domanda pubblica o disagio sociale e pochi ETS."""
    if not COMUNI_ETS_PATH.exists():
        return []
    where = "WHERE (appalti_riservati > 0 OR rd_pct > 5)"
    if provincia:
        where += f" AND provincia = '{provincia}'"
    df = con.sql(f"""
        SELECT comune as denominazione, provincia as sigla_provincia,
               popolazione as pop, reddito_procapite as reddito,
               appalti_riservati as appalti,
               ROUND(importo_anac_totale / 1000000, 1) as importo_M,
               ets_matchabili as ets_ok, ets_tot,
               rd_pct, nuclei_rdc,
               CASE
                 WHEN appalti_riservati >= 5 AND ets_matchabili < 5 THEN 'domanda pubblica alta, pochi ETS'
                 WHEN appalti_riservati >= 1 AND ets_matchabili = 0 THEN 'domanda pubblica, zero ETS'
                 WHEN ets_matchabili = 0 AND rd_pct > 10 THEN 'RdC alto, zero ETS'
                 WHEN ets_matchabili < 3 AND reddito_procapite > 0 AND reddito_procapite < 10000 THEN 'reddito basso, pochissimi ETS'
                 WHEN ets_matchabili = 0 AND reddito_procapite > 0 AND reddito_procapite < 12000 THEN 'reddito basso, zero ETS'
                 ELSE ''
               END as gap_segnale
        FROM '{COMUNI_ETS_PATH}'
        {where}
        ORDER BY appalti_riservati DESC, ets_matchabili ASC
        LIMIT {limite}
    """).fetchdf().to_dict("records")
    return [dict(r) for r in df]


# ── Vista territorio (segnale) ─────────────────────────────────────

def _v_scalar(df, col, default=None):
    if df is None or df.empty:
        return default
    v = df[col].iloc[0]
    if v is None or pd.isna(v):
        return default
    return v


def contesto_sociale(con, territorio, comune=None):
    """Reddito pro-capite (ultimo anno con dati) e RdC/PdC takeup.

    Media ponderata per popolazione. Se comune è valorizzato, si riferisce
    al comune; altrimenti all'intera provincia.
    """
    if comune:
        filtro_reddito = f"UPPER(denominazione) = '{comune.upper()}'"
        filtro_rdc = f"UPPER(comune) = '{comune.upper()}'"
        etichetta = f"Comune di {comune.title()}"
    else:
        filtro_reddito = f"sigla_provincia = '{territorio}'"
        filtro_rdc = f"sigla_provincia = '{territorio}'"
        etichetta = f"Provincia di {territorio}"

    out = {"etichetta": etichetta, "reddito": None, "anno_reddito": None, "rd_pct": None}
    try:
        df = con.sql(f"""
            SELECT SUM(reddito_procapite * popolazione_residente) / NULLIF(SUM(popolazione_residente), 0) as reddito,
                   ANY_VALUE(anno_reddito) as anno_reddito
            FROM '{UNIFIED_COMUNI_URL}',
                 (SELECT MAX(anno) as anno_reddito
                  FROM '{UNIFIED_COMUNI_URL}' WHERE reddito_procapite IS NOT NULL) t
            WHERE {filtro_reddito}
              AND anno = anno_reddito
              AND reddito_procapite IS NOT NULL
        """).fetchdf()
        out["reddito"] = _v_scalar(df, "reddito")
        anno = _v_scalar(df, "anno_reddito")
        out["anno_reddito"] = int(anno) if anno is not None else None
    except Exception:
        pass
    try:
        df = con.sql(f"""
            SELECT SUM(takeup * popolazione_residente) / NULLIF(SUM(popolazione_residente), 0) * 100 as rd_pct
            FROM '{INPS_RDC_URL}' WHERE {filtro_rdc}
        """).fetchdf()
        out["rd_pct"] = _v_scalar(df, "rd_pct")
    except Exception:
        pass
    return out


def ets_landscape(con, where):
    """Totale ETS, distribuzione per capacità e per tipologia."""
    tot = int(con.sql(f"SELECT count(*) FROM 'data/unified_ets.parquet' {where}").fetchone()[0])
    out = {"tot": tot, "per_capacita": [], "per_tipologia": []}
    for label, col in (("per_capacita", "capacita_progettuale"), ("per_tipologia", "sezione")):
        df = con.sql(f"SELECT {col} as grp, count(*) as n FROM 'data/unified_ets.parquet' {where} GROUP BY grp ORDER BY n DESC").fetchdf()
        out[label] = [{"grp": str(r["grp"]), "n": int(r["n"])} for _, r in df.iterrows()]
    return out


def bandi_match_locale(con, scan, territorio, comune=None):
    """Bandi attivi con match locale (ricalcolo con gate territorio)."""
    out = []
    for r in scan["resultados"]:
        if r.get("status") not in ("attivo", "sportello"):
            continue
        tags = r.get("tags", [])
        if not tags:
            continue
        b_orig = next((b for b in _bandi()
                       if str(b.get("titolo", "")) == str(r.get("titolo", ""))), None)
        testo = ""
        if b_orig:
            testo = " ".join(str(b_orig.get(k, "") or "") for k in
                             ("titolo", "descrizione", "obiettivi", "ammissibili", "testo_nlp"))
        df_locale = match_bando_funnel(con, tags, limit=1000 if comune else 20,
                                       territorio=[territorio], testo=testo)
        if comune:
            df_locale = df_locale[df_locale["comune"].str.upper() == comune.upper()]
            df_locale = df_locale.head(10)
        if df_locale.empty:
            continue
        candidati = []
        for _, c in df_locale.head(5).iterrows():
            candidati.append({
                "codice_fiscale": c.get("codice_fiscale"),
                "denominazione": str(c["denominazione"]),
                "comune": c.get("comune"),
                "provincia": c.get("provincia"),
                "capacita": c.get("capacita_progettuale"),
                "score": int(c.get("score") or 0),
                "motivo": fmt_match_reason(c),
                "importo_5x1000_2025": c.get("importo_5x1000_2025"),
            })
        gg = r.get("gg_rimasti", r.get("gg", 999))
        urgenza = "🔴" if gg <= 14 else "🟡" if gg <= 30 else "🟢"
        # Chiave di giunzione bidirezionale col CSV: id Infobandi se c'è,
        # altrimenti hash stabile dell'url (copre info_cooperazione/indicebandi).
        url = (b_orig.get("url") if b_orig else r.get("url")) or ""
        bando_id = b_orig.get("id") if (b_orig and b_orig.get("id") is not None) else f"url:{md5(url.encode()).hexdigest()[:12]}"
        out.append({
            "id": bando_id,
            "fonte": b_orig.get("fonte") if b_orig else r.get("fonte"),
            "url": url,
            "titolo": r["titolo"], "scadenza": r["scadenza"], "gg": gg, "ente": r["ente"],
            "tags": r.get("tags", []), "urgenza": urgenza,
            "candidati": candidati, "extra_candidati": max(len(df_locale) - 5, 0),
        })
    return out


def ets_riservati(con, where, limite=10):
    df = con.sql(f"""
        SELECT denominazione, comune, appalti_riservati, appalti_pnrr
        FROM 'data/unified_ets.parquet' {where}
          AND appalti_riservati > 0
        ORDER BY appalti_riservati DESC LIMIT {limite}
    """).fetchdf()
    return [{"denominazione": str(r["denominazione"]), "comune": r["comune"],
             "appalti_riservati": int(r["appalti_riservati"]), "appalti_pnrr": int(r["appalti_pnrr"] or 0)}
            for _, r in df.iterrows()]


def ets_immobili(con, where, limite=5):
    df = con.sql(f"""
        SELECT denominazione, comune, patrimonio_immobili, round(canone_totale, 0) as canone
        FROM 'data/unified_ets.parquet' {where}
          AND patrimonio_immobili > 0
        ORDER BY patrimonio_immobili DESC LIMIT {limite}
    """).fetchdf()
    return [{"denominazione": str(r["denominazione"]), "comune": r["comune"],
             "patrimonio_immobili": int(r["patrimonio_immobili"]), "canone": float(r["canone"] or 0)}
            for _, r in df.iterrows()]


def top_ets(con, where, limite=10):
    df = con.sql(f"""
        SELECT denominazione, comune, capacita_progettuale, importo_5x1000_2025
        FROM 'data/unified_ets.parquet' {where}
          AND capacita_progettuale IN ('media', 'medio-alta', 'alta')
        ORDER BY importo_5x1000_2025 DESC NULLS LAST LIMIT {limite}
    """).fetchdf()
    return [{"denominazione": str(r["denominazione"]), "comune": r["comune"],
             "capacita": r["capacita_progettuale"], "importo_5x1000_2025": r["importo_5x1000_2025"]}
            for _, r in df.iterrows()]


def ets_appalti_comune(con, comune, limite=10):
    df = con.sql(f"""
        SELECT denominazione, capacita_progettuale, ha_appalti_pubblici,
               ROUND(importo_appalti, 0) as importo
        FROM 'data/unified_ets.parquet'
        WHERE UPPER(comune) = '{comune.upper()}' AND ha_appalti_pubblici = true
        ORDER BY importo DESC LIMIT {limite}
    """).fetchdf()
    return [{"denominazione": str(r["denominazione"]), "capacita": r["capacita_progettuale"],
             "importo": float(r["importo"] or 0)} for _, r in df.iterrows()]


def gap_limitrofi(con, territorio, comune, limite=5):
    df = con.sql(f"""
        SELECT comune, provincia, ets_tot, ets_matchabili as ets_ok, appalti_riservati, rd_pct, reddito_procapite,
               CASE
                 WHEN appalti_riservati >= 5 AND ets_matchabili < 5 THEN '🔴 appalti ma pochi ETS'
                 WHEN ets_matchabili = 0 AND rd_pct > 10 THEN '🟡 RdC alto, zero ETS'
               END as segnale
        FROM 'data/comuni_ets.parquet'
        WHERE provincia = '{territorio}' AND (appalti_riservati > 0 OR rd_pct > 10)
          AND comune != '{comune.title()}'
        ORDER BY appalti_riservati DESC, ets_matchabili ASC LIMIT {limite}
    """).fetchdf()
    return [{"comune": str(r["comune"]), "provincia": r["provincia"], "ets_tot": int(r["ets_tot"]),
             "ets_ok": int(r["ets_ok"]), "appalti_riservati": int(r["appalti_riservati"] or 0),
             "rd_pct": float(r["rd_pct"] or 0), "reddito": float(r["reddito_procapite"] or 0),
             "segnale": r["segnale"] or ""} for _, r in df.iterrows()]


def vista_territorio(con, territorio, comune=None):
    """Vista completa per il segnale territoriale (JSON-serializzabile)."""
    where = f"WHERE provincia = '{territorio}'"
    if comune:
        where += f" AND UPPER(comune) = '{comune.upper()}'"
    titolo = comune or territorio
    return {
        "generato": datetime.now().isoformat(timespec="seconds"),
        "territorio": territorio,
        "comune": comune,
        "titolo": titolo,
        "ets_landscape": ets_landscape(con, where),
        "bandi_locali": bandi_match_locale(con, scan=load_scan_local(), territorio=territorio, comune=comune),
        "contesto": contesto_sociale(con, territorio, comune),
        "ets_riservati": ets_riservati(con, where),
        "ets_immobili": ets_immobili(con, where),
        "top_ets": top_ets(con, where),
        "ets_appalti": ets_appalti_comune(con, comune) if comune else [],
        "gap_limitrofi": gap_limitrofi(con, territorio, comune) if comune else [],
    }


# ── Vista latest ────────────────────────────────────────────────────

def vista_latest(scan, con, giorni=60, territorio=None):
    """Bandi in scadenza nei prossimi N giorni + gap territoriali."""
    oggi = datetime.now()
    risultati = []
    for r in scan["resultados"]:
        gg = r.get("gg_rimasti", r.get("gg", 999))
        if 0 <= gg <= giorni:
            r["gg"] = gg
            risultati.append(r)

    bandi = []
    for r in sorted(risultati, key=lambda x: x["gg"]):
        bandi.append({
            "titolo": r["titolo"], "ente": r.get("ente"), "scadenza": r["scadenza"],
            "gg": r["gg"], "url": r.get("url"), "status": r["status"],
            "territorio": r.get("territorio", []), "tags": r.get("tags", []),
            "candidati": [{
                "denominazione": c["denominazione"], "comune": c.get("comune"),
                "provincia": c.get("provincia"), "capacita": c.get("capacita", c.get("capacita_progettuale")),
                "score": int(c.get("score", 0)), "motivo": fmt_match_reason(c),
                "importo_5x1000_2025": c.get("importo_5x1000_2025"),
            } for c in r["candidati"][:5]],
        })

    top_budget = sorted([r for r in risultati if r.get("budget")], key=lambda x: -(x.get("budget") or 0))
    return {
        "generato": oggi.isoformat(timespec="seconds"),
        "giorni": giorni,
        "territorio": territorio,
        "tot_bandi": len(risultati),
        "bandi": bandi,
        "top_budget": [{"titolo": r["titolo"], "ente": r.get("ente"), "budget": r.get("budget"),
                        "gg": r.get("gg_rimasti", r.get("gg", 999)), "url": r.get("url")} for r in top_budget],
        "gap": gap_territoriale(con, provincia=territorio),
    }


# ── Caricamento scan condiviso ──────────────────────────────────────

def load_scan_local():
    """Legge radar-completo.json (scan condiviso da run_scan_completo)."""
    import json
    from config import RADAR_REPORT
    p = RADAR_REPORT.with_suffix(".json")
    if not p.exists():
        raise FileNotFoundError(f"{p} non trovato. Esegui scan_completo.py senza flag.")
    with open(p) as f:
        return json.load(f)
