#!/usr/bin/env python3
"""Costruisce data/comuni_ets.parquet — metriche consolidate per comune.

Una riga per comune italiano con tutte le metriche del Terzo Settore:
- ETS: conteggi per sezione, capacita, grant, PNRR, sport
- Appalti riservati ANAC (domanda pubblica di ETS)
- RdC + reddito (contesto sociale)
- Popolazione (per normalizzazione)

Output: ~7.900 righe, pronto per gap analysis, segnali, dashboard.
"""

import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))

import duckdb
import pandas as pd

from config import gcs_path, normalize_comune

ETS_FILE = str(ROOT / "data" / "unified_ets.parquet")
OUTPUT = str(ROOT / "data" / "comuni_ets.parquet")

ANAC_URLS = ", ".join(
    f"'{gcs_path('anac_bandi_gara', y)}'"
    for y in [2023, 2024, 2025]
)

t0 = time.time()


# ── 1. Base comuni: ISTAT + metriche ────────────────────────────────

def load_comuni(con):
    """Carica anagrafe comuni + popolazione + reddito + RdC."""
    print("📥 Carico anagrafe comuni...")
    df = con.sql(f"""
        SELECT codice_istat, denominazione, sigla_provincia
        FROM '{gcs_path("istat_elenco_comuni", 2026)}'
    """).fetchdf()
    
    print("📥 Carico popolazione e reddito...")
    metr = con.sql(f"""
        SELECT codice_istat,
               ROUND(popolazione_residente)::INT as pop,
               ROUND(reddito_procapite, 0)::INT as reddito
        FROM '{gcs_path("unified_comuni", 2026)}'
        WHERE anno = 2023
    """).fetchdf()
    
    print("📥 Carico RdC...")
    rdc = con.sql(f"""
        SELECT TRIM(comune) as c,
               ROUND(takeup * 100, 1) as rd_pct,
               ROUND(nuclei_familiari_percettori_rdc_luglio_2020)::INT as nuclei_rdc
        FROM '{gcs_path("inps_rdc_pdc", 2020)}'
    """).fetchdf()
    
    # Costruisce lookup: nome_normalizzato → (istat, prov)
    # e mappa: istat → (pop, reddito, rd_pct)
    lookup = {}
    istat_data = {}
    for _, r in df.iterrows():
        istat = str(r["codice_istat"]).strip()
        nome = str(r["denominazione"]).strip()
        prov = str(r["sigla_provincia"]).strip() if r["sigla_provincia"] and str(r["sigla_provincia"]) != "nan" else ""
        norm = normalize_comune(nome)
        if norm:
            lookup[norm] = (istat, prov)
    
    
    # Metriche per istat
    for _, r in metr.iterrows():
        istat = str(r["codice_istat"]).strip()
        istat_data.setdefault(istat, {})
        istat_data[istat]["pop"] = int(r["pop"]) if r["pop"] and not pd.isna(r["pop"]) else 0
        istat_data[istat]["reddito"] = int(r["reddito"]) if r["reddito"] and not pd.isna(r["reddito"]) else 0
    
    # RdC per istat (match via nome normalizzato)
    for _, r in rdc.iterrows():
        norm = normalize_comune(str(r["c"]))
        if norm and norm in lookup:
            istat = lookup[norm][0]
            if istat:
                istat_data.setdefault(istat, {})
                istat_data[istat]["rd_pct"] = float(r["rd_pct"]) if r["rd_pct"] and not pd.isna(r["rd_pct"]) else 0.0
                istat_data[istat]["nuclei_rdc"] = int(r["nuclei_rdc"]) if r["nuclei_rdc"] and not pd.isna(r["nuclei_rdc"]) else 0
    
    return lookup, istat_data


# ── 2. ANAC appalti riservati per codice_istat ──────────────────────

def load_anac(con):
    """Carica appalti riservati ANAC aggregati per codice ISTAT."""
    print("📥 Carico ANAC appalti riservati...")
    df = con.sql(f"""
        SELECT codice_istat_luogo as istat,
               COUNT(*)::INT as appalti_riservati,
               ROUND(SUM(importo_complessivo_gara), 0) as importo_anac_totale
        FROM read_parquet([{ANAC_URLS}], union_by_name=true)
        WHERE TIPO_APPALTO_RISERVATO NOT IN ('', 'LA PARTECIPAZIONE NON È RISERVATA.')
          AND TIPO_APPALTO_RISERVATO IS NOT NULL
          AND codice_istat_luogo IS NOT NULL AND codice_istat_luogo != ''
        GROUP BY codice_istat_luogo
    """).fetchdf()
    result = {}
    for _, r in df.iterrows():
        istat = str(r["istat"]).strip()
        result[istat] = {
            "appalti_riservati": int(r["appalti_riservati"]),
            "importo_anac_totale": float(r["importo_anac_totale"]) if r["importo_anac_totale"] and not pd.isna(r["importo_anac_totale"]) else 0.0,
        }
    return result


# ── 3. ETS aggregati per comune ─────────────────────────────────────

def load_ets(con):
    """Carica ETS aggregati per comune normalizzato."""
    print("📥 Carico ETS...")
    df = con.sql(f"""
        SELECT TRIM(comune) as c, provincia, sezione, capacita_progettuale,
               ha_finanziamenti_ue, ha_progetti_pnrr, ha_sport_in_denominazione,
               CASE WHEN capacita_progettuale IN ('media','medio-alta','alta') THEN 1 ELSE 0 END as matchabile,
               CASE WHEN capacita_progettuale = 'alta' THEN 1 ELSE 0 END as capacita_alta,
               CASE WHEN capacita_progettuale = 'medio-alta' THEN 1 ELSE 0 END as capacita_medio_alta,
               CASE WHEN capacita_progettuale = 'media' THEN 1 ELSE 0 END as capacita_media,
               CASE WHEN sezione = 'ORGANIZZAZIONI DI VOLONTARIATO' THEN 1 ELSE 0 END as odv,
               CASE WHEN sezione = 'ASSOCIAZIONI DI PROMOZIONE SOCIALE' THEN 1 ELSE 0 END as aps,
               CASE WHEN sezione = 'IMPRESE SOCIALI' THEN 1 ELSE 0 END as imprese_sociali,
               CASE WHEN sezione = 'ENTI FILANTROPICI' THEN 1 ELSE 0 END as enti_filantropici,
               CASE WHEN sezione = 'ALTRI ENTI DEL TERZO SETTORE' THEN 1 ELSE 0 END as altri_enti,
               CASE WHEN sezione = 'SOCIETA'' DI MUTUO SOCCORSO' THEN 1 ELSE 0 END as sms
        FROM '{ETS_FILE}'
        WHERE comune IS NOT NULL AND comune != ''
    """).fetchdf()
    
    # Aggrega per nome normalizzato
    agg = {}
    for _, r in df.iterrows():
        norm = normalize_comune(r["c"])
        if not norm:
            continue
        if norm not in agg:
            agg[norm] = {k: 0 for k in [
                "ets_tot", "ets_matchabili", "capacita_alta", "capacita_medio_alta", "capacita_media",
                "odv", "aps", "imprese_sociali", "enti_filantropici", "altri_enti", "sms",
                "con_grant_ue", "con_pnrr", "sport",
                "con_appalti",
            ]}
        agg[norm]["ets_tot"] += 1
        agg[norm]["ets_matchabili"] += int(r["matchabile"])
        agg[norm]["capacita_alta"] += int(r["capacita_alta"])
        agg[norm]["capacita_medio_alta"] += int(r["capacita_medio_alta"])
        agg[norm]["capacita_media"] += int(r["capacita_media"])
        agg[norm]["odv"] += int(r["odv"])
        agg[norm]["aps"] += int(r["aps"])
        agg[norm]["imprese_sociali"] += int(r["imprese_sociali"])
        agg[norm]["enti_filantropici"] += int(r["enti_filantropici"])
        agg[norm]["altri_enti"] += int(r["altri_enti"])
        agg[norm]["sms"] += int(r["sms"])
        agg[norm]["con_grant_ue"] += 1 if r["ha_finanziamenti_ue"] else 0
        agg[norm]["con_pnrr"] += 1 if r["ha_progetti_pnrr"] else 0
        agg[norm]["sport"] += 1 if r["ha_sport_in_denominazione"] else 0
    
    return agg


# ── 3b. ANAC aggiudicatari (chi vince gli appalti) + importi ───────────

ANAC_AGGIUDICATARI_GCS = gcs_path("anac_aggiudicatari", 2026)
ANAC_AGGIUDICAZIONI_GCS = gcs_path("anac_aggiudicazioni", 2026)


def _join_aggiudicatari_importi():
    """JOIN aggiudicatari (GCS) -> aggiudicazioni (GCS) per importi per CF.
    
    Legge entrambi i dataset direttamente da GCS, nessun download locale.
    Restituisce dict: cf -> {n_appalti, importo_totale}.
    """
    print("📥 JOIN aggiudicatari -> aggiudicazioni (GCS)...")
    con = duckdb.connect()
    df = con.sql(f"""
        SELECT a.codice_fiscale as cf,
               COUNT(*)::INT as n_appalti,
               ROUND(SUM(ag.importo_aggiudicazione), 0) as importo_totale
        FROM '{ANAC_AGGIUDICATARI_GCS}' a
        JOIN '{ANAC_AGGIUDICAZIONI_GCS}' ag ON a.cig = ag.cig
        WHERE ag.importo_aggiudicazione > 0
          AND ag.importo_aggiudicazione < 100000000000
          AND EXTRACT(YEAR FROM ag.data_aggiudicazione_definitiva) BETWEEN 2000 AND 2026
        GROUP BY a.codice_fiscale
    """).fetchdf()
    con.close()
    
    result = {}
    for _, r in df.iterrows():
        cf = str(r["cf"]).strip()
        if cf and len(cf) >= 11:
            result[cf] = {
                "n_appalti": int(r["n_appalti"]),
                "importo_totale": float(r["importo_totale"]),
            }
    print(f"   {len(result):,} CF con importi")
    return result


def load_aggiudicatari(con, ets_agg):
    """Aggrega ETS con appalti ANAC per comune (legge da GCS).
    
    Aggiunge a ets_agg:
    - con_appalti: ETS con almeno un appalto
    - con_appalti_importo: ETS con importo noto
    - importo_appalti_totale: somma importi per comune
    """
    aggiudicatari = _join_aggiudicatari_importi()
    
    df = con.sql(f"""
        SELECT codice_fiscale, TRIM(comune) as c, provincia
        FROM '{ETS_FILE}'
        WHERE codice_fiscale IS NOT NULL AND codice_fiscale != ''
          AND comune IS NOT NULL AND comune != ''
    """).fetchdf()
    
    cf_ets_set = set(df["codice_fiscale"].tolist())
    cf_match = cf_ets_set & set(aggiudicatari.keys())
    print(f"   CF ETS con appalti: {len(cf_match):,}")
    
    df_match = df[df["codice_fiscale"].isin(cf_match)]
    for _, r in df_match.iterrows():
        norm = normalize_comune(r["c"])
        if not norm or norm not in ets_agg:
            continue
        data = aggiudicatari.get(r["codice_fiscale"], {})
        
        for k in ("con_appalti", "con_appalti_importo"):
            ets_agg[norm].setdefault(k, 0)
        ets_agg[norm].setdefault("importo_appalti_totale", 0.0)
        
        ets_agg[norm]["con_appalti"] += 1
        imp = data.get("importo_totale", 0)
        if imp > 0:
            ets_agg[norm]["con_appalti_importo"] += 1
            ets_agg[norm]["importo_appalti_totale"] += imp
    
    for norm in ets_agg:
        for k in ("con_appalti", "con_appalti_importo"):
            ets_agg[norm].setdefault(k, 0)
        ets_agg[norm].setdefault("importo_appalti_totale", 0.0)
    
    return cf_match


# ── 4. Build finale ─────────────────────────────────────────────────

def main():
    con = duckdb.connect()
    
    lookup, istat_data = load_comuni(con)
    anac_data = load_anac(con)
    ets_agg = load_ets(con)
    
    # Aggiudicatari ANAC: ETS che vincono appalti
    cf_match = load_aggiudicatari(con, ets_agg)
    con.close()
    
    print("🔗 Join e scrittura...")
    rows = []
    seen_istat = set()
    # Prima ISTAT (nomi ufficiali), poi SPECIAL_COMUNI solo se ISTAT non visto
    # Ordine: prima i nomi ISTAT esatti, poi gli alias SPECIAL_COMUNI
    items_istat = [(n, i, p) for n, (i, p) in lookup.items() if i not in seen_istat and not seen_istat.add(i)]
    seen_istat.clear()
    items = []
    for n, i, p in items_istat:
        items.append((n, i, p, True))
        seen_istat.add(i)
    for n, (i, p) in lookup.items():
        if i not in seen_istat:
            items.append((n, i, p, False))
            seen_istat.add(i)
    
    for norm, istat, prov, _is_primary in items:
        if not istat:
            continue
        
        md = istat_data.get(istat, {})
        an = anac_data.get(istat, {})
        et = ets_agg.get(norm, {})
        
        appalti = an.get("appalti_riservati", 0)
        
        rows.append({
            "codice_istat": istat,
            "comune": norm.title(),  # normalized display name
            "provincia": prov,
            "popolazione": md.get("pop", 0),
            "reddito_procapite": md.get("reddito", 0),
            "rd_pct": md.get("rd_pct", 0.0),
            "nuclei_rdc": md.get("nuclei_rdc", 0),
            "appalti_riservati": appalti,
            "importo_anac_totale": round(an.get("importo_anac_totale", 0), 0),
            **{k: et.get(k, 0) for k in [
                "ets_tot", "ets_matchabili",
                "capacita_alta", "capacita_medio_alta", "capacita_media",
                "odv", "aps", "imprese_sociali", "enti_filantropici", "altri_enti", "sms",
                "con_grant_ue", "con_pnrr", "sport",
                "con_appalti", "con_appalti_importo", "importo_appalti_totale",
            ]},
            # Derivate
            "ets_sconosciuti": et.get("ets_tot", 0) - et.get("ets_matchabili", 0),
            "appalti_per_10k_ets": round(appalti / max(et.get("ets_tot", 1), 1) * 10000, 1),
        })
    
    df_out = pd.DataFrame(rows)
    df_out.to_parquet(OUTPUT, index=False)
    
    elapsed = time.time() - t0
    print(f"\n✅ {len(df_out)} comuni in {OUTPUT}")
    print(f"   {df_out['ets_tot'].sum():.0f} ETS totali")
    print(f"   {df_out['appalti_riservati'].sum():.0f} appalti riservati ANAC")
    print(f"   {df_out['con_appalti'].sum():.0f} ETS con appalti ANAC")
    print(f"   {df_out['con_appalti_importo'].sum():.0f} ETS con importo noto")
    print(f"   €{df_out['importo_appalti_totale'].sum()/1e9:.1f} Mld importo totale")
    print(f"   Tempo: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
