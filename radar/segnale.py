#!/usr/bin/env python3
"""Segnale — report unico territorio.

Usa core.run_scan() per il matching bandi, poi filtra per territorio
e aggiunge analisi ETS locale (landscape, gap sociali, top candidati).

Uso:
    python radar/segnale.py --territorio MI
    python radar/segnale.py --territorio MI --comune Abbiategrasso
"""

import json, sys
from datetime import datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))

from config import gcs_path, REGION_PROVINCES
from radar.core import fmt_euro, fmt_match_reason, fmt_tags, fmt_text, is_missing

RADAR_JSON = ROOT / "cruscotto" / "radar-completo.json"
UNIFIED_COMUNI_URL = gcs_path("unified_comuni", 2026)
INPS_RDC_URL = gcs_path("inps_rdc_pdc", 2020)


def load_scan():
    if not RADAR_JSON.exists():
        print(f"❌ {RADAR_JSON} non trovato. Esegui prima scan_completo.py")
        sys.exit(1)
    with open(RADAR_JSON) as f:
        return json.load(f)


def scrivi(out, testo=""):
    out.append(testo)


def report(territorio: str, comune: str = None):
    out = []
    oggi = datetime.now()
    con = duckdb.connect()

    where = f"WHERE provincia = '{territorio}'"
    if comune:
        where += f" AND UPPER(comune) = '{comune.upper()}'"

    titolo_territorio = comune or territorio

    scrivi(out, f"# 📡 Segnali — {titolo_territorio}")
    scrivi(out, f"Generato: {oggi.strftime('%d/%m/%Y %H:%M')}")
    scrivi(out, "")

    # ── 1. ETS Landscape ────────────────────────────────────────────
    scrivi(out, "## 1. 🏛️  ETS sul territorio")
    scrivi(out, "")

    ets_tot = con.sql(f"SELECT count(*) FROM 'data/unified_ets.parquet' {where}").fetchone()[0]
    scrivi(out, f"**{ets_tot} ETS** totali.")
    scrivi(out, "")

    cap_counts = con.sql(f"""
        SELECT capacita_progettuale, count(*) as n
        FROM 'data/unified_ets.parquet' {where}
        GROUP BY capacita_progettuale ORDER BY n DESC
    """).fetchdf()
    scrivi(out, "**Per capacità:**")
    for _, r in cap_counts.iterrows():
        icon = {"sconosciuta": "⬜", "base": "🟨", "media": "🟦", "medio-alta": "🔷", "alta": "🟢"}.get(r["capacita_progettuale"], "⬜")
        scrivi(out, f"  {icon} **{r['capacita_progettuale']}**: {r['n']} ETS")
    scrivi(out, "")

    sez_counts = con.sql(f"""
        SELECT sezione, count(*) as n
        FROM 'data/unified_ets.parquet' {where}
        GROUP BY sezione ORDER BY n DESC
    """).fetchdf()
    scrivi(out, "**Per tipologia:**")
    for _, r in sez_counts.iterrows():
        scrivi(out, f"  · {r['sezione']}: {r['n']}")
    scrivi(out, "")

    # ── 2. Match bandi sul territorio (da radar-completo.json) ─────────
    scrivi(out, "## 2. 📋 Bandi con match locale")
    scrivi(out, "")

    scan = load_scan()
    # Filtra resultados per territorio: candidati nel territorio
    match_locali = 0
    for r in scan["resultados"]:
        candidati_locali = [c for c in r["candidati"]
                           if str(c.get("provincia", "") or "").upper() == territorio.upper()
                           and (not comune or str(c.get("comune", "") or "").upper() == comune.upper())]
        if candidati_locali:
            match_locali += 1
            gg = r.get("gg_rimasti", r.get("gg", 999))
            urgenza = "🔴" if gg <= 14 else "🟡" if gg <= 30 else "🟢"
            scrivi(out, f"### {urgenza} {r['titolo'][:80]}")
            scrivi(out, f"- **Scadenza**: {r['scadenza']} ({gg} giorni)")
            scrivi(out, f"- **Ente**: {r['ente']}")
            scrivi(out, f"- **Tag**: {fmt_tags(r['tags'])}")
            scrivi(out, "")
            for c in candidati_locali[:5]:
                cinque = fmt_euro(c.get("importo_5x1000_2025"))
                cap = c.get("capacita", c.get("capacita_progettuale", "?"))
                scrivi(out, f"  · **{cap}** {c['denominazione'][:50]} "
                       f"— {fmt_text(c.get('comune'), '')} — score {int(c.get('score', 0))}, "
                       f"{fmt_match_reason(c)} — 5x1000: {cinque}")
            if len(candidati_locali) > 5:
                scrivi(out, f"  *...e altri {len(candidati_locali)-5} candidati*")
            scrivi(out, "")

    if match_locali == 0:
        scrivi(out, "_Nessun bando con match locale._")
        scrivi(out, "")

    # ── 3. Gap sociali ─────────────────────────────────────────────
    scrivi(out, "## 3. 📊 Contesto sociale")
    scrivi(out, "")

    try:
        reddito = con.sql(f"""
            SELECT round(reddito_procapite) as reddito,
                   round(tasso_occupazione, 1) as occupazione
            FROM '{UNIFIED_COMUNI_URL}'
            WHERE provincia = '{territorio}' AND anno = 2024
            ORDER BY reddito_procapite
            LIMIT 1
        """).fetchdf()
        if not reddito.empty:
            scrivi(out, f"- **Reddito pro-capite**: €{reddito['reddito'].iloc[0]:,}")
            scrivi(out, f"- **Tasso occupazione**: {reddito['occupazione'].iloc[0]}%")
    except Exception:
        pass

    try:
        rdc = con.sql(f"""
            SELECT round(takeup * 100, 1) as rd_pct
            FROM '{INPS_RDC_URL}'
            WHERE lower(comune) = '{titolo_territorio.lower()}'
        """).fetchdf()
        if not rdc.empty:
            scrivi(out, f"- **RdC/PdC takeup**: {rdc['rd_pct'].iloc[0]}%")
    except Exception:
        pass
    scrivi(out, "")

    # ── 4. Top ETS per capacità ────────────────────────────────────
    scrivi(out, "## 4. 🏆 Top ETS per capacità progettuale")
    scrivi(out, "")
    top = con.sql(f"""
        SELECT codice_fiscale, denominazione, comune, capacita_progettuale, importo_5x1000_2025
        FROM 'data/unified_ets.parquet'
        {where} AND capacita_progettuale IN ('media', 'medio-alta', 'alta')
        ORDER BY importo_5x1000_2025 DESC NULLS LAST
        LIMIT 10
    """).fetchdf()
    if not top.empty:
        for _, r in top.iterrows():
            cinque = fmt_euro(r.get("importo_5x1000_2025"))
            scrivi(out, f"  · **{r['capacita_progettuale']}** {r['denominazione'][:50]} — {r['comune']} — 5x1000: {cinque}")
    scrivi(out, "")

    # ── 5. ETS nel comune con appalti ANAC ──────────────────────────
    if comune:
        scrivi(out, "## 5. 📊 ETS con appalti pubblici (ANAC)")
        scrivi(out, "")
        appalti = con.sql(f"""
            SELECT denominazione, capacita_progettuale, ha_finanziamenti_ue, ha_progetti_pnrr,
                   CASE WHEN ha_appalti_pubblici THEN 'SI' ELSE 'NO' END as ha_appalti_pubblici,
                   ROUND(importo_appalti, 0) as importo
            FROM 'data/unified_ets.parquet'
            WHERE UPPER(comune) = '{comune.upper()}'
              AND ha_appalti_pubblici = true
            ORDER BY importo DESC
            LIMIT 10
        """).fetchdf()
        if not appalti.empty:
            for _, r in appalti.iterrows():
                imp = f"€{float(r['importo']):,.0f}" if r['importo'] and float(r['importo']) > 0 else "-"
                scrivi(out, f"  · **{r['denominazione'][:45]}** [{r['capacita_progettuale']}] — appalti: {imp}")
        else:
            scrivi(out, "_Nessun ETS con appalti pubblici._")
        scrivi(out, "")

        # Gap: comuni vicini con pochi ETS
        scrivi(out, "## 6. 📍 Gap nei comuni limitrofi")
        scrivi(out, "")
        gap = con.sql(f"""
            SELECT comune, provincia, ets_tot, ets_matchabili as ets_ok,
                   appalti_riservati, rd_pct, reddito_procapite,
                   CASE 
                     WHEN appalti_riservati >= 5 AND ets_matchabili < 5 THEN '🔴 appalti ma pochi ETS'
                     WHEN ets_matchabili = 0 AND rd_pct > 10 THEN '🟡 RdC alto, zero ETS'
                     ELSE NULL
                   END as segnale
            FROM 'data/comuni_ets.parquet'
            WHERE provincia = '{territorio}'
              AND (appalti_riservati > 0 OR rd_pct > 10)
              AND comune != '{comune.title()}'
            ORDER BY appalti_riservati DESC, ets_matchabili ASC
            LIMIT 5
        """).fetchdf()
        if not gap.empty:
            for _, r in gap.iterrows():
                s = r['segnale'] or ""
                scrivi(out, f"  · **{r['comune'][:20]}** ({r['provincia']}) — {int(r['ets_tot'])} ETS, RdC {r['rd_pct']}%, reddito €{int(r['reddito_procapite']):,} {s}")
        else:
            scrivi(out, "_Tutti i comuni limitrofi hanno ETS sufficienti._")
    
    report_path = ROOT / f"cruscotto/segnale-{titolo_territorio.lower()}.md"
    report_path.write_text("\n".join(out), encoding="utf-8")
    print(f"✅ Report: {report_path}")


def provincia(sigla: str) -> str:
    """Ritorna il nome della provincia data la sigla. Inverte REGION_PROVINCES."""
    prov_to_name = {p: name for name, provs in REGION_PROVINCES.items() for p in provs}
    return prov_to_name.get(sigla.upper(), sigla)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--territorio", required=True, help="Sigla provincia (es. MI)")
    parser.add_argument("--comune", help="Comune (opzionale)")
    args = parser.parse_args()
    report(args.territorio, args.comune)
