#!/usr/bin/env python3
"""Vista latest del radar: bandi operativi in scadenza nei prossimi 60 giorni."""

import json, sys
from datetime import datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))

from radar.core import fmt_euro, fmt_match_reason, fmt_tags, fmt_text
from patterns import normalize_comune

ETS_FILE = ROOT / "data" / "unified_ets.parquet"
RADAR_JSON = ROOT / "cruscotto" / "radar-completo.json"
GCS_BASE = "https://storage.googleapis.com/dataciviclab-clean"
INPS_RDC_URL = f"{GCS_BASE}/inps_rdc_pdc/2020/inps_rdc_pdc_2020_clean.parquet"
COMUNI_URL = f"{GCS_BASE}/istat_elenco_comuni/2026/istat_elenco_comuni_2026_clean.parquet"
UNIFIED_COMUNI_URL = f"{GCS_BASE}/unified_comuni/2026/unified_comuni_2026_clean.parquet"
_COMUNI_LOOKUP = None  # cache per _build_comune_lookup

ANAC_URLS = ", ".join(
    f"'{GCS_BASE}/anac_bandi_gara/{y}/anac_bandi_gara_{y}_clean.parquet'"
    for y in [2023, 2024, 2025]
)


def load_scan():
    """Carica scan da JSON già calcolato."""
    if not RADAR_JSON.exists():
        print(f"❌ {RADAR_JSON} non trovato. Esegui prima scan_completo.py")
        sys.exit(1)
    with open(RADAR_JSON) as f:
        return json.load(f)


def _build_comune_lookup(con=None):
    """Costruisce mapping nome_normalizzato → (codice_istat, provincia).
    
    Usa normalize_comune() (NFD+ASCII per accenti, apostrofi, bilingui)
    e integra SPECIAL_COMUNI per fusioni, bilingui, casi anomali.
    Cache in memoria (variabile globale _COMUNI_LOOKUP).
    """
    global _COMUNI_LOOKUP
    if _COMUNI_LOOKUP is not None:
        return _COMUNI_LOOKUP
    
    from patterns import SPECIAL_COMUNI
    import pandas as pd
    close_con = con is None
    if con is None:
        con = duckdb.connect()
    
    df = con.sql(f"SELECT codice_istat, denominazione, sigla_provincia FROM '{COMUNI_URL}'").fetchdf()
    if close_con:
        con.close()
    
    # lookup: nome_normalizzato → (codice_istat, provincia)
    # istat_nome: codice_istat → nome ISTAT originale (per display)
    lookup = {}
    istat_nome = {}
    for _, r in df.iterrows():
        istat = str(r["codice_istat"]).strip()
        nome_orig = str(r["denominazione"]).strip()
        prov = str(r["sigla_provincia"]).strip() if r["sigla_provincia"] and str(r["sigla_provincia"]) != "nan" else ""
        norm = normalize_comune(nome_orig)
        if norm:
            lookup[norm] = (istat, prov)
            if istat not in istat_nome:
                istat_nome[istat] = nome_orig
    
    # SPECIAL_COMUNI: aggiunge nomi alternativi per comuni gia' esistenti
    for nome, istat in SPECIAL_COMUNI.items():
        norm = normalize_comune(nome)
        if norm:
            if norm not in lookup:
                prov = ""
                # cerca provincia dal nome principale se possibile
                for k, (i, p) in lookup.items():
                    if i == istat and p:
                        prov = p
                        break
                lookup[norm] = (istat, prov)
    
    _COMUNI_LOOKUP = (lookup, istat_nome)
    return lookup, istat_nome


def gap_territoriale(con):
    """Gap analysis: incrocia ANAC appalti riservati + ETS + RdC + reddito.
    
    I nomi dei comuni sono normalizzati con normalize_comune()
    (NFD+ASCII, apostrofi, SPECIAL_COMUNI per fusioni/bilingui)
    per massimizzare il match tra fonti diverse.
    """
    import pandas as pd
    import math
    
    # 1. ANAC: aggregato per codice_istat (in DuckDB, via GCS)
    df_anac = con.sql(f"""
        SELECT codice_istat_luogo as istat,
               COUNT(*)::INT as appalti,
               ROUND(SUM(importo_complessivo_gara), 0) as importo_totale
        FROM read_parquet([{ANAC_URLS}], union_by_name=true)
        WHERE TIPO_APPALTO_RISERVATO NOT IN ('', 'LA PARTECIPAZIONE NON È RISERVATA.')
          AND TIPO_APPALTO_RISERVATO IS NOT NULL
          AND codice_istat_luogo IS NOT NULL AND codice_istat_luogo != ''
        GROUP BY codice_istat_luogo
    """).fetchdf()
    anac_map = {r["istat"]: (int(r["appalti"]), float(r["importo_totale"]))
                for _, r in df_anac.iterrows()}
    
    # 2. Metriche: unificate per codice_istat
    df_metr = con.sql(f"""
        SELECT codice_istat as istat,
               ROUND(popolazione_residente)::INT as pop,
               ROUND(reddito_procapite, 0)::INT as reddito
        FROM '{UNIFIED_COMUNI_URL}'
        WHERE anno = 2023
    """).fetchdf()
    metr_map = {r["istat"]: (int(r["pop"]) if r["pop"] and not pd.isna(r["pop"]) else 0,
                              int(r["reddito"]) if r["reddito"] and not pd.isna(r["reddito"]) else 0)
                for _, r in df_metr.iterrows()}
    
    # 3. Costruisce lookup comuni (cached)
    lookup, istat_nome = _build_comune_lookup(con)
    
    # 4. ETS: normalizza nomi e aggrega
    df_ets = con.sql(f"""
        SELECT TRIM(comune) as c, provincia,
               CASE WHEN capacita_progettuale IN ('media','medio-alta','alta') THEN 1 ELSE 0 END as ok
        FROM '{ETS_FILE.as_posix()}'
        WHERE comune IS NOT NULL AND comune != ''
    """).fetchdf()
    ets_agg = {}
    for _, r in df_ets.iterrows():
        norm = normalize_comune(r["c"])
        prov = str(r["provincia"]).strip() if r["provincia"] and str(r["provincia"]) not in ("nan", "-", "") else ""
        if norm:
            if norm not in ets_agg:
                ets_agg[norm] = {"ets_tot": 0, "ets_ok": 0, "prov": ""}
            ets_agg[norm]["ets_tot"] += 1
            ets_agg[norm]["ets_ok"] += int(r["ok"])
            if prov:
                ets_agg[norm]["prov"] = prov
    
    # 5. RdC: normalizza nomi
    df_rdc = con.sql(f"""
        SELECT DISTINCT TRIM(comune) as c,
               ROUND(takeup * 100, 1) as rd_pct,
               ROUND(nuclei_familiari_percettori_rdc_luglio_2020)::INT as nuclei
        FROM '{INPS_RDC_URL}'
    """).fetchdf()
    rdc_map = {}
    for _, r in df_rdc.iterrows():
        norm = normalize_comune(r["c"])
        if norm and r["rd_pct"] and not pd.isna(r["rd_pct"]):
            rdc_map[norm] = (float(r["rd_pct"]),
                             int(r["nuclei"]) if r["nuclei"] and not pd.isna(r["nuclei"]) else 0)
    
    # 6. JOIN in Python
    rows = []
    seen_istat = set()
    for norm, (istat, prov) in lookup.items():
        appalti, importo_tot = anac_map.get(istat, (0, 0))
        pop, reddito = metr_map.get(istat, (0, 0))
        ets = ets_agg.get(norm, {"ets_tot": 0, "ets_ok": 0, "prov": ""})
        rd_pct, nuclei = rdc_map.get(norm, (0, 0))
        
        # Filtra: solo comuni con appalti o con gap sociale
        if appalti == 0 and rd_pct <= 5:
            continue
        
        # Usa il nome ISTAT originale (evita duplicati "Roma"/"Roma Capitale")
        nome_display = istat_nome.get(istat, norm.title())
        
        # Deduplica per ISTAT (se gia' visto, salta — tiene primo nome)
        if istat in seen_istat:
            continue
        seen_istat.add(istat)
        
        # Segnale
        if appalti >= 5 and ets["ets_ok"] < 5:
            segnale = "🔴 domanda pubblica alta, pochi ETS"
        elif appalti >= 1 and ets["ets_ok"] == 0:
            segnale = "🟠 domanda pubblica, zero ETS"
        elif ets["ets_ok"] == 0 and rd_pct > 10:
            segnale = "🟡 RdC alto, zero ETS"
        else:
            segnale = ""
        
        rows.append({
            "denominazione": nome_display,
            "sigla_provincia": prov,
            "pop": pop, "reddito": reddito,
            "appalti": appalti, "importo_M": round(importo_tot / 1_000_000, 1),
            "ets_ok": ets["ets_ok"], "ets_tot": ets["ets_tot"],
            "rd_pct": rd_pct, "nuclei_rdc": nuclei,
            "gap_segnale": segnale,
        })
    
    df_out = pd.DataFrame(rows)
    if df_out.empty:
        return []
    
    # Ordina: appalti desc, ets_ok asc
    df_out = df_out.sort_values(["appalti", "ets_ok"], ascending=[False, True]).head(10)
    return df_out.to_dict("records")


def territory_matches(r, filtro_territorio):
    if not filtro_territorio:
        return True
    needle = filtro_territorio.lower()
    territory = " ".join(r.get("territorio", [])).lower()
    candidates = " ".join(
        f"{fmt_text(c.get('comune'), '')} {fmt_text(c.get('provincia'), '')}".lower()
        for c in r.get("candidati", [])
    )
    return needle in territory or needle in candidates


def genera_report(scan, con, filtro_territorio=None, giorni=60):
    oggi = datetime.now()
    risultati = []
    for r in scan["resultados"]:
        gg = r.get("gg_rimasti", r.get("gg", 999))
        if 0 <= gg <= giorni and territory_matches(r, filtro_territorio):
            r["gg"] = gg  # normalizza
            risultati.append(r)

    lines = []
    lines.append(f"# 📡 Radar bandi — {oggi.strftime('%d/%m/%Y')}")
    lines.append("")
    lines.append(f"Bandi operativi in scadenza nei prossimi {giorni}gg: **{len(risultati)}**")
    if filtro_territorio:
        lines.append(f"Filtro territorio: **{filtro_territorio}**")
    lines.append("")

    for r in sorted(risultati, key=lambda x: x["gg"]):
        lines.append(f"## {r['titolo'][:80]}")
        lines.append(f"- **Ente**: {r['ente'] or '?'}")
        lines.append(f"- **Scadenza**: {r['scadenza']} ({r['gg']} giorni)")
        lines.append(f"- **Stato**: {r['status']}")
        lines.append(f"- **Territorio**: {', '.join(r['territorio'])}")
        lines.append(f"- **Tag**: {fmt_tags(r['tags'])}")
        lines.append("")
        for c in r["candidati"][:5]:
            comune = fmt_text(c.get("comune"), "")
            provincia = fmt_text(c.get("provincia"))
        cap = c.get("capacita", c.get("capacita_progettuale", "?"))
        lines.append(
            f"  · **{cap}** {c['denominazione'][:55]} "
            f"— {comune} ({provincia}) — score {int(c.get('score', 0))}, "
            f"{fmt_match_reason(c)} — 5x1000: {fmt_euro(c.get('cinque_2025'))}"
        )
        lines.append("")

    lines.append("---")
    lines.append("## ⚠️ Gap territoriali (appalti riservati ANAC + ETS + RdC)")
    lines.append("")
    lines.append("| Comune | Prov | Appalti riservati | ETS ok | RdC% | Reddito | Segnale |")
    lines.append("|--------|------|------------------|--------|------|---------|---------|")
    for g in gap_territoriale(con):
        segnale = g.get("gap_segnale", "") or ""
        lines.append(
            f"| {g['denominazione'][:20]} | {g['sigla_provincia']} "
            f"| {g['appalti']} app. €{g['importo_M']}M "
            f"| {g['ets_ok']} | {g['rd_pct']}% "
            f"| €{g['reddito']:,} | {segnale} |"
        )
    lines.append("")
    lines.append(f"_Vista latest da scan condiviso: {len(scan['resultados'])} bandi operativi matchati. "
                 f"Dati ANAC: appalti riservati (L.381/1991, D.Lgs 117/2017) 2023-2025._")
    return "\n".join(lines)


def main():
    filtro = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--territorio" else None
    con = duckdb.connect()
    scan = load_scan()
    report = genera_report(scan, con, filtro_territorio=filtro)
    out = ROOT / "cruscotto" / "radar-latest.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(f"✅ Radar salvato: {out}")
    print(report[:2000])


if __name__ == "__main__":
    main()
