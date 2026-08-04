#!/usr/bin/env python3
"""Scan: matcha bandi, report, filtri.

Usage:
    python match/reports/scan_completo.py              # scan + radar-completo.json + .md
    python match/reports/scan_completo.py --latest     # bandi ≤60gg → radar-latest.md
    python match/reports/scan_completo.py --territorio MI [--comune X]  # segnale-MI.md
"""

import argparse, json, sys
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))

from config import RADAR_REPORT, gcs_path, REGION_PROVINCES
from lib.format import fmt_euro, fmt_match_reason, fmt_tags, fmt_text
from match.pipeline import run_scan
from match.funnel import match_bando_funnel

RADAR_JSON = RADAR_REPORT.with_suffix(".json")
COMUNI_ETS_PATH = Path(__file__).resolve().parents[2] / "data" / "comuni_ets.parquet"
UNIFIED_COMUNI_URL = gcs_path("unified_comuni", 2026)
INPS_RDC_URL = gcs_path("inps_rdc_pdc", 2020)


def scrivi(lines, s=""):
    lines.append(s)


def load_scan():
    if not RADAR_JSON.exists():
        print(f"❌ {RADAR_JSON} non trovato. Esegui scan_completo.py senza flag.")
        sys.exit(1)
    with open(RADAR_JSON) as f:
        return json.load(f)


def gap_territoriale(con, limite=10, provincia=None):
    if not COMUNI_ETS_PATH.exists():
        return []
    where = "WHERE appalti_riservati > 0 OR rd_pct > 5"
    if provincia:
        where += f" AND provincia = '{provincia}'"
    return con.sql(f"""
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


def report_latest(scan, con, giorni=60, territorio=None):
    oggi = datetime.now()
    risultati = []
    for r in scan["resultados"]:
        gg = r.get("gg_rimasti", r.get("gg", 999))
        if 0 <= gg <= giorni:
            r["gg"] = gg
            risultati.append(r)

    lines = []
    scrivi(lines, f"# 📡 Radar bandi — {oggi.strftime('%d/%m/%Y')}")
    scrivi(lines, "")
    scrivi(lines, f"Bandi operativi in scadenza nei prossimi {giorni}gg: **{len(risultati)}**")
    if territorio:
        scrivi(lines, f"Filtro territorio: **{territorio}**")
    scrivi(lines, "")

    for r in sorted(risultati, key=lambda x: x["gg"]):
        scrivi(lines, f"## {r['titolo'][:80]}")
        scrivi(lines, f"- **Ente**: {r['ente'] or '?'}")
        scrivi(lines, f"- **Scadenza**: {r['scadenza']} ({r['gg']} giorni)")
        scrivi(lines, f"- **Link**: {r.get('url', '?')}")
        scrivi(lines, f"- **Stato**: {r['status']}")
        scrivi(lines, f"- **Territorio**: {', '.join(r['territorio'])}")
        scrivi(lines, f"- **Tag**: {fmt_tags(r['tags'])}")
        scrivi(lines, "")
        for c in r["candidati"][:5]:
            cap = c.get("capacita", c.get("capacita_progettuale", "?"))
            scrivi(lines, f"  · **{cap}** {c['denominazione'][:55]} "
                   f"— {fmt_text(c.get('comune'), '')} ({fmt_text(c.get('provincia'))}) "
                   f"— score {int(c.get('score', 0))}, {fmt_match_reason(c)} "
                   f"— 5x1000: {fmt_euro(c.get('importo_5x1000_2025'))}")
        scrivi(lines, "")

    con_budget = [r for r in risultati if r.get("budget")]
    if con_budget:
        scrivi(lines, "---")
        scrivi(lines, "## TOP OPPORTUNITÀ (bandi con budget)")
        scrivi(lines, "")
        scrivi(lines, "| Budget | GG | Ente | Bando | Link |")
        scrivi(lines, "|--------|----|------|-------|------|")
        for r in sorted(con_budget, key=lambda x: -(x.get("budget") or 0)):
            urg = " (🔴)" if r.get("gg", 999) <= 30 else (" (🟡)" if r.get("gg", 999) <= 60 else "")
            scrivi(lines, f"| {fmt_euro(r.get('budget'))}{urg} | {r.get('gg', 999)}gg "
                   f"| {fmt_text(r['ente'], '?')[:30]} | {r['titolo'][:40]} | [link]({r.get('url', '?')[:50]}) |")
        scrivi(lines, "")

    scrivi(lines, "---")
    scrivi(lines, "## Gap territoriali (appalti ANAC + ETS + contesto sociale)")
    scrivi(lines, "")
    scrivi(lines, "| Comune | Prov | Appalti riservati | ETS ok | RdC% | Reddito | Segnale |")
    scrivi(lines, "|--------|------|------------------|--------|------|---------|---------|")
    for g in gap_territoriale(con, provincia=territorio):
        segnale = g.get("gap_segnale", "") or ""
        scrivi(lines, f"| {g['denominazione'][:20]} | {g['sigla_provincia']} "
               f"| {g['appalti']} app. €{g['importo_M']}M | {g['ets_ok']} | {g['rd_pct']}% "
               f"| €{g['reddito']:,} | {segnale} |")
    scrivi(lines, "")
    scrivi(lines, f"_Vista latest da scan condiviso: {len(scan['resultados'])} bandi operativi matchati._")
    return "\n".join(lines)


def report_territorio(scan, con, territorio: str, comune: str = None):
    from match.pipeline import load_bandi
    global _bandi_cache
    _bandi_cache = load_bandi()
    out = []
    oggi = datetime.now()
    where = f"WHERE provincia = '{territorio}'"
    if comune:
        where += f" AND UPPER(comune) = '{comune.upper()}'"
    titolo_territorio = comune or territorio

    scrivi(out, f"# 📡 Segnali — {titolo_territorio}")
    scrivi(out, f"Generato: {oggi.strftime('%d/%m/%Y %H:%M')}")
    scrivi(out, "")

    # ETS Landscape
    scrivi(out, "## 1. 🏛️  ETS sul territorio")
    scrivi(out, "")
    ets_tot = con.sql(f"SELECT count(*) FROM 'data/unified_ets.parquet' {where}").fetchone()[0]
    scrivi(out, f"**{ets_tot} ETS** totali.")
    scrivi(out, "")
    for label in ["Per capacità:", "Per tipologia:"]:
        col = "capacita_progettuale" if "capacità" in label else "sezione"
        df = con.sql(f"SELECT {col} as grp, count(*) as n FROM 'data/unified_ets.parquet' {where} GROUP BY grp ORDER BY n DESC").fetchdf()
        if not df.empty:
            scrivi(out, f"**{label}**")
            for _, r in df.iterrows():
                scrivi(out, f"  · {r['grp']}: {r['n']}")
            scrivi(out, "")

    # Bandi con match locale — ricalcola il match COL GATE territorio,
    # così il rank è locale (le ODV/APS del comune non vengono schiacciate
    # dalle grandi organizzazioni nazionali nel rank globale).
    scrivi(out, "## 2. 📋 Bandi con match locale")
    scrivi(out, "")
    match_locali = 0
    for r in scan["resultados"]:
        if r.get("status") not in ("attivo", "sportello"):
            continue
        tags = r.get("tags", [])
        if not tags:
            continue
        # testo del bando per il fallback del funnel (dal catalogo bandi)
        b_orig = next((b for b in _bandi_cache
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
        match_locali += 1
        gg = r.get("gg_rimasti", r.get("gg", 999))
        urgenza = "🔴" if gg <= 14 else "🟡" if gg <= 30 else "🟢"
        scrivi(out, f"### {urgenza} {r['titolo'][:80]}")
        scrivi(out, f"- **Scadenza**: {r['scadenza']} ({gg} giorni)")
        scrivi(out, f"- **Ente**: {r['ente']}")
        scrivi(out, f"- **Tag**: {fmt_tags(r['tags'])}")
        scrivi(out, "")
        for _, c in df_locale.head(5).iterrows():
            cap = c.get("capacita_progettuale", "?")
            scrivi(out, f"  · **{cap}** {c['denominazione'][:50]} "
                   f"— {fmt_text(c.get('comune'), '')} — score {int(c['score'] or 0)}, "
                   f"{fmt_match_reason(c)} — 5x1000: {fmt_euro(c.get('importo_5x1000_2025'))}")
        if len(df_locale) > 5:
            scrivi(out, f"  *...e altri {len(df_locale) - 5} candidati*")
        scrivi(out, "")
    if match_locali == 0:
        scrivi(out, "_Nessun bando con match locale._")
        scrivi(out, "")

    # Contesto sociale
    scrivi(out, "## 3. 📊 Contesto sociale")
    scrivi(out, "")
    # Aggregazione provinciale: media ponderata per popolazione, anno = ultimo con dati
    # (il 2025 esiste nello schema ma reddito_procapite è NULL ovunque → si usa 2024 finché non pubblica)
    if comune:
        filtro_reddito = f"UPPER(denominazione) = '{comune.upper()}'"
        filtro_rdc = f"UPPER(comune) = '{comune.upper()}'"
        etichetta = f"Comune di {comune.title()}"
    else:
        filtro_reddito = f"sigla_provincia = '{territorio}'"
        filtro_rdc = f"sigla_provincia = '{territorio}'"
        etichetta = f"Provincia di {territorio}"
    scrivi(out, f"_{etichetta} — media ponderata per popolazione._")
    scrivi(out, "")
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
        if not df.empty and df['reddito'].iloc[0] and not pd.isna(df['reddito'].iloc[0]):
            scrivi(out, f"- **Reddito pro-capite** ({int(df['anno_reddito'].iloc[0])}): €{int(df['reddito'].iloc[0]):,}")
    except Exception:
        pass
    try:
        df = con.sql(f"""
            SELECT SUM(takeup * popolazione_residente) / NULLIF(SUM(popolazione_residente), 0) * 100 as rd_pct
            FROM '{INPS_RDC_URL}' WHERE {filtro_rdc}
        """).fetchdf()
        if not df.empty and df['rd_pct'].iloc[0] and not pd.isna(df['rd_pct'].iloc[0]):
            scrivi(out, f"- **RdC/PdC takeup** (2020): {df['rd_pct'].iloc[0]:.1f}%")
    except Exception:
        pass
    scrivi(out, "")

    # ETS con appalti riservati
    riservati = con.sql(f"""
        SELECT denominazione, comune, appalti_riservati, appalti_pnrr
        FROM 'data/unified_ets.parquet' {where}
          AND appalti_riservati > 0
        ORDER BY appalti_riservati DESC LIMIT 10
    """).fetchdf()
    if not riservati.empty:
        scrivi(out, "## 4. 📋 ETS con appalti riservati")
        scrivi(out, "")
        for _, r in riservati.iterrows():
            pnrr = f" — PNRR: {int(r['appalti_pnrr'])}" if r['appalti_pnrr'] > 0 else ""
            scrivi(out, f"  · **{r['denominazione'][:50]}** — {r['comune']} — {int(r['appalti_riservati'])} riservati{pnrr}")
        scrivi(out, "")

    # ETS con immobili pubblici
    immobili = con.sql(f"""
        SELECT denominazione, comune, patrimonio_immobili, round(canone_totale, 0) as canone
        FROM 'data/unified_ets.parquet' {where}
          AND patrimonio_immobili > 0
        ORDER BY patrimonio_immobili DESC LIMIT 5
    """).fetchdf()
    if not immobili.empty:
        scrivi(out, "## 5. 🏠 ETS con immobili pubblici")
        scrivi(out, "")
        for _, r in immobili.iterrows():
            can = f" — €{float(r['canone']):,.0f}/anno" if r['canone'] > 0 else " — gratuito"
            scrivi(out, f"  · **{r['denominazione'][:50]}** — {r['comune']} — {int(r['patrimonio_immobili'])} immobili{can}")
        scrivi(out, "")

    # Top ETS
    scrivi(out, "## 6. 🏆 Top ETS per capacità progettuale")
    scrivi(out, "")
    top = con.sql(f"""
        SELECT denominazione, comune, capacita_progettuale, importo_5x1000_2025
        FROM 'data/unified_ets.parquet' {where}
          AND capacita_progettuale IN ('media', 'medio-alta', 'alta')
        ORDER BY importo_5x1000_2025 DESC NULLS LAST LIMIT 10
    """).fetchdf()
    if not top.empty:
        for _, r in top.iterrows():
            scrivi(out, f"  · **{r['capacita_progettuale']}** {r['denominazione'][:50]} "
                   f"— {r['comune']} — 5x1000: {fmt_euro(r.get('importo_5x1000_2025'))}")
    scrivi(out, "")

    # ANAC appalti
    if comune:
        scrivi(out, "## 6. 📊 ETS con appalti pubblici (ANAC)")
        scrivi(out, "")
        df = con.sql(f"""
            SELECT denominazione, capacita_progettuale, ha_appalti_pubblici,
                   ROUND(importo_appalti, 0) as importo
            FROM 'data/unified_ets.parquet'
            WHERE UPPER(comune) = '{comune.upper()}' AND ha_appalti_pubblici = true
            ORDER BY importo DESC LIMIT 10
        """).fetchdf()
        if not df.empty:
            for _, r in df.iterrows():
                imp = f"€{float(r['importo']):,.0f}" if r['importo'] and float(r['importo']) > 0 else "-"
                scrivi(out, f"  · **{r['denominazione'][:45]}** [{r['capacita_progettuale']}] — appalti: {imp}")
        else:
            scrivi(out, "_Nessun ETS con appalti pubblici._")
        scrivi(out, "")

        scrivi(out, "## 7. 📍 Gap nei comuni limitrofi")
        scrivi(out, "")
        df = con.sql(f"""
            SELECT comune, provincia, ets_tot, ets_matchabili as ets_ok, appalti_riservati, rd_pct, reddito_procapite,
                   CASE
                     WHEN appalti_riservati >= 5 AND ets_matchabili < 5 THEN '🔴 appalti ma pochi ETS'
                     WHEN ets_matchabili = 0 AND rd_pct > 10 THEN '🟡 RdC alto, zero ETS'
                   END as segnale
            FROM 'data/comuni_ets.parquet'
            WHERE provincia = '{territorio}' AND (appalti_riservati > 0 OR rd_pct > 10)
              AND comune != '{comune.title()}'
            ORDER BY appalti_riservati DESC, ets_matchabili ASC LIMIT 5
        """).fetchdf()
        if not df.empty:
            for _, r in df.iterrows():
                s = r['segnale'] or ""
                scrivi(out, f"  · **{r['comune'][:20]}** ({r['provincia']}) "
                       f"— {int(r['ets_tot'])} ETS, RdC {r['rd_pct']}%, reddito €{int(r['reddito_procapite']):,} {s}")
        else:
            scrivi(out, "_Tutti i comuni limitrofi hanno ETS sufficienti._")

    report_path = Path(__file__).resolve().parents[2] / f"cruscotto/segnale-{titolo_territorio.lower()}.md"
    report_path.write_text("\n".join(out), encoding="utf-8")
    print(f"✅ Report: {report_path}")


def report_completo(bandi, resultados, sin_match, skipped, stats_ets):
    lines = []
    scrivi(lines, "# 📡 Radar Completo — Tutti i Bandi vs ETS")
    scrivi(lines, f"Generato: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    scrivi(lines, "")
    scrivi(lines, f"**{len(resultados)}** bandi operativi con ETS candidabili  |  "
           f"**{len(sin_match)}** operativi senza match  |  "
           f"**{len(skipped)}** esclusi  |  **{len(stats_ets)}** ETS unici coinvolti")
    scrivi(lines, "")
    scrivi(lines, "---")
    scrivi(lines, "")

    urgenti = [r for r in resultados if r["gg"] <= 30]
    if urgenti:
        scrivi(lines, "## 🔴 Bandi urgenti (≤30gg) con ETS candidabili")
        scrivi(lines, "")
        for r in sorted(urgenti, key=lambda x: x["gg"]):
            urgenza = "🔴" if r["gg"] <= 14 else "🟡"
            scrivi(lines, f"### {urgenza} {r['titolo'][:80]}")
            scrivi(lines, f"- **Scadenza**: {r['scadenza']} ({r['gg']} giorni)")
            scrivi(lines, f"- **Ente**: {r['ente']}")
            scrivi(lines, f"- **Stato**: {r['status']}")
            scrivi(lines, f"- **Territorio**: {', '.join(r['territorio'])}")
            scrivi(lines, f"- **Tag**: {fmt_tags(r['tags'])}")
            scrivi(lines, "")
            scrivi(lines, "| ETS | Comune | Prov | Capacità | Score | Motivo | 5x1000 2025 |")
            scrivi(lines, "|-----|--------|------|----------|-------|--------|-------------|")
            for c in r["candidati"]:
                cinque = fmt_euro(c.get("importo_5x1000_2025"))
                comune = fmt_text(c.get("comune"), "")[:20]
                provincia = fmt_text(c.get("provincia"))
                scrivi(lines, f"| {c['denominazione'][:45]} | {comune} | {provincia} | "
                       f"{c['capacita_progettuale']} | {int(c.get('score', 0))} | "
                       f"{fmt_match_reason(c)} | {cinque} |")
            scrivi(lines, "")

    non_urgenti = [r for r in resultados if r["gg"] > 30]
    if non_urgenti:
        scrivi(lines, "## 🟢 Bandi con ETS candidabili (>30gg)")
        scrivi(lines, "")
        for r in sorted(non_urgenti, key=lambda x: x["gg"]):
            scrivi(lines, f"### {r['titolo'][:80]}")
            scrivi(lines, f"- **Scadenza**: {r['scadenza']} ({r['gg']} giorni)")
            scrivi(lines, f"- **Ente**: {r['ente']}")
            scrivi(lines, f"- **Stato**: {r['status']}")
            scrivi(lines, f"- **Territorio**: {', '.join(r['territorio'])}")
            scrivi(lines, f"- **Tag**: {fmt_tags(r['tags'])}")
            scrivi(lines, "")
            for c in r["candidati"]:
                cinque = fmt_euro(c.get("importo_5x1000_2025"))
                comune = fmt_text(c.get("comune"), "")
                provincia = fmt_text(c.get("provincia"))
                scrivi(lines, f"  · **{c['capacita_progettuale']}** {c['denominazione'][:50]} "
                       f"— {comune} ({provincia}) — score {int(c.get('score', 0))}, "
                       f"{fmt_match_reason(c)} — 5x1000: {cinque}")
            scrivi(lines, "")

    if sin_match:
        scrivi(lines, "---")
        scrivi(lines, "## ⚠️ Bandi senza ETS candidabili")
        scrivi(lines, "")
        for titolo, url, ente, scad, gg, tags, territorio, status, motivo in sorted(sin_match, key=lambda x: x[4]):
            emoji = "🔴" if gg <= 30 else "🟡" if gg <= 60 else "⚪"
            scrivi(lines, f"- {emoji} **{titolo[:70]}** — {ente} — scad. {scad} ({gg}gg) — _{motivo}_")
            scrivi(lines, f"  Stato: {status} | Territorio: {', '.join(territorio)} | Tag: {fmt_tags(tags)}")

    if skipped:
        scrivi(lines, "")
        scrivi(lines, "---")
        scrivi(lines, "## Esclusi dal matching")
        scrivi(lines, "")
        counts = {}
        for s in skipped:
            counts[s["status"]] = counts.get(s["status"], 0) + 1
        scrivi(lines, ", ".join(f"**{status}**: {count}" for status, count in sorted(counts.items())))
        scrivi(lines, "")
        for s in skipped[:20]:
            scrivi(lines, f"- **{s['titolo'][:80]}** — {s['status']} — {s['motivo']}")

    scrivi(lines, "")
    scrivi(lines, "---")
    scrivi(lines, f"_{len(bandi)} bandi processati, {len(resultados)} match trovati, "
           f"{len(sin_match)} gap operativi, {len(skipped)} esclusi._")
    return "\n".join(lines)


def run_scan_completo():
    scan = run_scan()
    report = report_completo(scan["bandi"], scan["resultados"], scan["sin_match"], scan["skipped"], scan["stats_ets"])
    RADAR_REPORT.write_text(report, encoding="utf-8")
    print(f"✅ Markdown: {RADAR_REPORT}")

    json_out = {
        "generato": datetime.now().isoformat(),
        "bandi_totali": len(scan["bandi"]),
        "match": len(scan["resultados"]),
        "gap": len(scan["sin_match"]),
        "esclusi": len(scan["skipped"]),
        "ets_unici": len(scan["stats_ets"]),
        "resultados": [
            {"titolo": r["titolo"], "url": r["url"], "ente": r["ente"], "budget": r.get("budget"),
             "scadenza": r["scadenza"], "gg_rimasti": r["gg"], "status": r["status"],
             "territorio": r["territorio"], "tags": r["tags"],
             "candidati": [{"cf": cand.get("codice_fiscale"), "denominazione": cand["denominazione"],
                            "comune": cand.get("comune"), "provincia": cand.get("provincia"),
                            "capacita": cand["capacita_progettuale"], "sezione": cand.get("sezione"),
                            "score": int(cand.get("score", 0)), "motivo": fmt_match_reason(cand),
                            "importo_5x1000_2025": cand.get("importo_5x1000_2025")} for cand in r["candidati"]]}
            for r in scan["resultados"]
        ],
        "sin_match": [{"titolo": t[0], "url": t[1], "ente": t[2], "scadenza": t[3],
                       "gg_rimasti": t[4], "tags": t[5], "territorio": t[6], "status": t[7], "motivo": t[8]}
                      for t in scan["sin_match"]],
        "esclusi": [{"titolo": s["titolo"], "status": s["status"], "motivo": s["motivo"]} for s in scan["skipped"]],
    }
    RADAR_JSON.write_text(json.dumps(json_out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ JSON:      {RADAR_JSON}")


def main():
    parser = argparse.ArgumentParser(description="Scan bandi e report")
    parser.add_argument("--latest", action="store_true", help="Bandi ≤60gg → radar-latest.md")
    parser.add_argument("--territorio", help="Provincia (es. MI) → segnale-{T}.md")
    parser.add_argument("--comune", help="Comune (opzionale, con --territorio)")
    parser.add_argument("--giorni", type=int, default=60, help="Giorni per --latest (default 60)")
    args = parser.parse_args()

    if args.latest:
        scan = load_scan()
        con = duckdb.connect()
        report = report_latest(scan, con, giorni=args.giorni, territorio=args.territorio)
        out = Path(__file__).resolve().parents[2] / "cruscotto" / "radar-latest.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"✅ Radar salvato: {out}")
    elif args.territorio:
        scan = load_scan()
        con = duckdb.connect()
        report_territorio(scan, con, args.territorio.upper(), args.comune)
    else:
        run_scan_completo()


if __name__ == "__main__":
    main()
