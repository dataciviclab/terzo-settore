#!/usr/bin/env python3
"""Vista latest del radar: bandi operativi in scadenza nei prossimi 60 giorni."""

import json, sys
from datetime import datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))

from lib.format import fmt_euro, fmt_match_reason, fmt_tags, fmt_text

RADAR_JSON = ROOT / "cruscotto" / "radar-completo.json"
COMUNI_ETS_PATH = ROOT / "data" / "comuni_ets.parquet"


def load_scan():
    """Carica scan da JSON già calcolato."""
    if not RADAR_JSON.exists():
        print(f"❌ {RADAR_JSON} non trovato. Esegui prima scan_completo.py")
        sys.exit(1)
    with open(RADAR_JSON) as f:
        return json.load(f)


def gap_territoriale(con):
    """Gap analysis: comuni con appalti riservati ANAC o gap sociale."""
    if not COMUNI_ETS_PATH.exists():
        return []
    return con.sql(f"""
        SELECT comune as denominazione, provincia as sigla_provincia,
               popolazione as pop, reddito_procapite as reddito,
               appalti_riservati as appalti,
               ROUND(importo_anac_totale / 1000000, 1) as importo_M,
               ets_matchabili as ets_ok, ets_tot,
               rd_pct, nuclei_rdc,
               CASE
                 WHEN appalti_riservati >= 5 AND ets_matchabili < 5 THEN '🔴 domanda pubblica alta, pochi ETS'
                 WHEN appalti_riservati >= 1 AND ets_matchabili = 0 THEN '🟠 domanda pubblica, zero ETS'
                 WHEN ets_matchabili = 0 AND rd_pct > 10 THEN '🟡 RdC alto, zero ETS'
                 WHEN ets_matchabili < 3 AND reddito_procapite > 0 AND reddito_procapite < 10000 THEN '🟠 reddito basso, pochissimi ETS'
                 WHEN ets_matchabili = 0 AND reddito_procapite > 0 AND reddito_procapite < 12000 THEN '🟠 reddito basso, zero ETS'
                 ELSE ''
               END as gap_segnale
        FROM '{COMUNI_ETS_PATH}'
        WHERE appalti_riservati > 0 OR rd_pct > 5
        ORDER BY appalti_riservati DESC, ets_matchabili ASC
        LIMIT 10
    """).fetchdf().to_dict("records")


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
        lines.append(f"- **Link**: {r.get('url', '?')}")
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
            f"{fmt_match_reason(c)} — 5x1000: {fmt_euro(c.get('importo_5x1000_2025'))}"
        )
        lines.append("")

    # ── Sezione 20/80: bandi con budget ──
    con_budget = [r for r in risultati if r.get("budget")]
    if con_budget:
        lines.append("")
        lines.append("---")
        lines.append("## 💰 TOP OPPORTUNITÀ (bandi con budget)")
        lines.append("")
        lines.append(f"| Budget | GG | Ente | Bando | Link |")
        lines.append(f"|--------|----|------|-------|------|")
        for r in sorted(con_budget, key=lambda x: -(x.get("budget") or 0)):
            budget = fmt_euro(r.get("budget"))
            gg = r.get("gg", 999)
            urg = " 🔴" if gg <= 30 else (" 🟡" if gg <= 60 else "")
            url_short = r.get('url', '?')[:50]
            lines.append(f"| {budget}{urg} | {gg}gg | {fmt_text(r['ente'], '?')[:30]} | {r['titolo'][:40]} | [link]({url_short}) |")
        lines.append("")

    lines.append("---")
    lines.append("## ⚠️ Gap territoriali (appalti ANAC + ETS + contesto sociale)")
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
