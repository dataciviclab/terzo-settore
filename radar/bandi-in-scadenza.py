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

ETS_FILE = ROOT / "data" / "unified_ets.parquet"
RADAR_JSON = ROOT / "cruscotto" / "radar-completo.json"
GCS_BASE = "https://storage.googleapis.com/dataciviclab-clean"
INPS_RDC_URL = f"{GCS_BASE}/inps_rdc_pdc/2020/inps_rdc_pdc_2020_clean.parquet"
COMUNI_URL = f"{GCS_BASE}/istat_elenco_comuni/2026/istat_elenco_comuni_2026_clean.parquet"
UNIFIED_COMUNI_URL = f"{GCS_BASE}/unified_comuni/2026/unified_comuni_2026_clean.parquet"
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


def gap_territoriale(con):
    """Gap analysis: incrocia ANAC appalti riservati + ETS + RdC + reddito.
    
    Usa istat_elenco_comuni come base (tutti i comuni italiani), 
    unified_comuni per metriche socioeconomiche.
    Normalizza apostrofi per massimizzare match con ETS.
    """
    r = con.sql(f"""
        WITH anac AS (
            SELECT codice_istat_luogo,
                   COUNT(*)::INT as appalti_riservati,
                   ROUND(SUM(importo_complessivo_gara), 0) as importo_totale
            FROM read_parquet([{ANAC_URLS}], union_by_name=true)
            WHERE TIPO_APPALTO_RISERVATO NOT IN ('', 'LA PARTECIPAZIONE NON È RISERVATA.')
              AND TIPO_APPALTO_RISERVATO IS NOT NULL
              AND codice_istat_luogo IS NOT NULL AND codice_istat_luogo != ''
            GROUP BY codice_istat_luogo
        ),
        -- Base: tutti i comuni da ISTAT (7889 comuni, vs 7512 di unified_comuni)
        comuni AS (
            SELECT codice_istat, denominazione, sigla_provincia,
                   REPLACE(LOWER(TRIM(denominazione)), '''', '') as denom_norm
            FROM '{COMUNI_URL}'
        ),
        -- Metriche socioeconomiche da unified_comuni (solo per comuni presenti)
        metriche AS (
            SELECT codice_istat,
                   ROUND(popolazione_residente)::INT as pop,
                   ROUND(reddito_procapite, 0)::INT as reddito
            FROM '{UNIFIED_COMUNI_URL}'
            WHERE anno = 2023
        ),
        -- ETS raggruppati per comune (nome normalizzato senza apostrofi)
        ets_locali AS (
            SELECT 
                REPLACE(LOWER(TRIM(comune)), '''', '') as c_norm,
                provincia,
                COUNT(*)::INT as ets_tot,
                SUM(CASE WHEN capacita_progettuale IN ('media','medio-alta','alta') THEN 1 ELSE 0 END)::INT as ets_ok
            FROM '{ETS_FILE.as_posix()}'
            WHERE comune IS NOT NULL AND comune != ''
            GROUP BY REPLACE(LOWER(TRIM(comune)), '''', ''), provincia
        ),
        rdc AS (
            SELECT 
                REPLACE(LOWER(TRIM(comune)), '''', '') as c_norm,
                ROUND(takeup * 100, 1) as rd_pct,
                ROUND(nuclei_familiari_percettori_rdc_luglio_2020)::INT as nuclei
            FROM '{INPS_RDC_URL}'
        )
        SELECT c.denominazione, c.sigla_provincia,
               COALESCE(m.pop, 0)::INT as pop,
               COALESCE(m.reddito, 0)::INT as reddito,
               COALESCE(a.appalti_riservati, 0)::INT as appalti,
               COALESCE(ROUND(a.importo_totale / 1000000, 1), 0) as importo_M,
               COALESCE(e.ets_ok, 0)::INT as ets_ok,
               COALESCE(e.ets_tot, 0)::INT as ets_tot,
               COALESCE(r.rd_pct, 0) as rd_pct,
               COALESCE(r.nuclei, 0)::INT as nuclei_rdc,
               CASE
                 WHEN COALESCE(a.appalti_riservati, 0) >= 5 AND COALESCE(e.ets_ok, 0) < 5 THEN '🔴 domanda pubblica alta, pochi ETS'
                 WHEN COALESCE(a.appalti_riservati, 0) >= 1 AND COALESCE(e.ets_ok, 0) = 0 THEN '🟠 domanda pubblica, zero ETS'
                 WHEN COALESCE(e.ets_ok, 0) = 0 AND COALESCE(r.rd_pct, 0) > 10 THEN '🟡 RdC alto, zero ETS'
                 ELSE NULL
               END as gap_segnale
        FROM comuni c
        LEFT JOIN metriche m ON c.codice_istat = m.codice_istat
        LEFT JOIN anac a ON c.codice_istat = a.codice_istat_luogo
        LEFT JOIN ets_locali e ON c.denom_norm = e.c_norm 
                              AND c.sigla_provincia = COALESCE(NULLIF(e.provincia, ''), c.sigla_provincia)
        LEFT JOIN rdc r ON c.denom_norm = r.c_norm
        WHERE COALESCE(a.appalti_riservati, 0) >= 1 
           OR (COALESCE(e.ets_ok, 0) = 0 AND COALESCE(r.rd_pct, 0) > 5)
        ORDER BY a.appalti_riservati DESC NULLS LAST, e.ets_ok ASC
        LIMIT 10
    """).fetchdf()
    records = r.to_dict("records")
    import math
    for rec in records:
        segnale = rec.get("gap_segnale")
        if segnale is None or (isinstance(segnale, float) and math.isnan(segnale)):
            rec["gap_segnale"] = ""
    return records


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
