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


def load_scan():
    """Carica scan da JSON già calcolato."""
    if not RADAR_JSON.exists():
        print(f"❌ {RADAR_JSON} non trovato. Esegui prima scan_completo.py")
        sys.exit(1)
    with open(RADAR_JSON) as f:
        return json.load(f)


def gap_rcd(con):
    r = con.sql(
        f"""
        SELECT i.comune, round(i.takeup * 100, 1) as rd_pct,
               i.nuclei_familiari_percettori_rdc_luglio_2020 as nuclei,
               COALESCE(e.ets_count, 0) as ets
        FROM '{INPS_RDC_URL}' i
        LEFT JOIN (
            SELECT lower(comune) as c, count(*) as ets_count
            FROM '{ETS_FILE.as_posix()}'
            GROUP BY lower(comune)
        ) e ON lower(i.comune) = e.c
        WHERE i.takeup > 0.05 AND (e.ets_count IS NULL OR e.ets_count < 5)
        ORDER BY i.takeup DESC
        LIMIT 5
    """
    ).fetchdf()
    return r.to_dict("records")


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
    lines.append("## ⚠️ Gap territoriali (RdC alto, pochi ETS)")
    lines.append("")
    for g in gap_rcd(con):
        ets_str = f"{int(g['ets'])} ETS" if g["ets"] else "zero ETS"
        lines.append(f"- **{g['comune'].title()}**: RdC {g['rd_pct']}%, {int(g['nuclei'])} nuclei, {ets_str}")
    lines.append("")
    lines.append(f"_Vista latest da scan condiviso: {len(scan['resultados'])} bandi operativi matchati._")
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
