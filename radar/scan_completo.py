#!/usr/bin/env python3
"""Scan completo: matcha tutti i bandi contro unified_ets.
Produce cruscotto/radar-completo.md"""

import json, sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from config import RADAR_REPORT
from radar.core import fmt_euro, fmt_match_reason, fmt_tags, fmt_text, run_scan

RADAR_JSON = RADAR_REPORT.with_suffix(".json")


def scrivi(lines, s=""):
    lines.append(s)


def genera_report(bandi, resultados, sin_match, skipped, stats_ets):
    lines = []

    scrivi(lines, "# 📡 Radar Completo — Tutti i Bandi vs ETS")
    scrivi(lines, f"Generato: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    scrivi(lines, "")
    scrivi(
        lines,
        f"**{len(resultados)}** bandi operativi con ETS candidabili  |  "
        f"**{len(sin_match)}** operativi senza match  |  "
        f"**{len(skipped)}** esclusi  |  **{len(stats_ets)}** ETS unici coinvolti",
    )
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
                cinque = fmt_euro(c.get("cinque_2025"))
                comune = fmt_text(c.get("comune"), "")[:20]
                provincia = fmt_text(c.get("provincia"))
                scrivi(
                    lines,
                    f"| {c['denominazione'][:45]} | {comune} | {provincia} | "
                    f"{c['capacita_progettuale']} | {int(c.get('score', 0))} | "
                    f"{fmt_match_reason(c)} | {cinque} |",
                )
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
                cinque = fmt_euro(c.get("cinque_2025"))
                comune = fmt_text(c.get("comune"), "")
                provincia = fmt_text(c.get("provincia"))
                scrivi(
                    lines,
                    f"  · **{c['capacita_progettuale']}** {c['denominazione'][:50]} "
                    f"— {comune} ({provincia}) — score {int(c.get('score', 0))}, "
                    f"{fmt_match_reason(c)} — 5x1000: {cinque}",
                )
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
    scrivi(
        lines,
        f"_{len(bandi)} bandi processati, {len(resultados)} match trovati, "
        f"{len(sin_match)} gap operativi, {len(skipped)} esclusi._",
    )
    return "\n".join(lines)


def main():
    scan = run_scan()
    report = genera_report(
        scan["bandi"],
        scan["resultados"],
        scan["sin_match"],
        scan["skipped"],
        scan["stats_ets"],
    )
    RADAR_REPORT.write_text(report, encoding="utf-8")
    print(f"✅ Markdown: {RADAR_REPORT}")

    # Output JSON strutturato
    json_out = {
        "generato": datetime.now().isoformat(),
        "bandi_totali": len(scan["bandi"]),
        "match": len(scan["resultados"]),
        "gap": len(scan["sin_match"]),
        "esclusi": len(scan["skipped"]),
        "ets_unici": len(scan["stats_ets"]),
        "resultados": [
            {
                "titolo": r["titolo"],
                "url": r["url"],
                "ente": r["ente"],
                "budget": r.get("budget"),
                "scadenza": r["scadenza"],
                "gg_rimasti": r["gg"],
                "status": r["status"],
                "territorio": r["territorio"],
                "tags": r["tags"],
                    "candidati": [
                        {
                            "cf": cand.get("codice_fiscale"),
                            "denominazione": cand["denominazione"],
                            "comune": cand.get("comune"),
                            "provincia": cand.get("provincia"),
                            "capacita": cand["capacita_progettuale"],
                            "sezione": cand.get("sezione"),
                            "score": int(cand.get("score", 0)),
                            "motivo": fmt_match_reason(cand),
                            "cinque_2025": cand.get("cinque_2025"),
                        }
                        for cand in r["candidati"]
                    ],
            }
            for r in scan["resultados"]
        ],
        "sin_match": [
            {
                "titolo": t[0], "url": t[1], "ente": t[2],
                "scadenza": t[3], "gg_rimasti": t[4],
                "tags": t[5], "territorio": t[6], "status": t[7], "motivo": t[8],
            }
            for t in scan["sin_match"]
        ],
        "esclusi": [
            {"titolo": s["titolo"], "status": s["status"], "motivo": s["motivo"]}
            for s in scan["skipped"]
        ],
    }
    RADAR_JSON.write_text(json.dumps(json_out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ JSON:      {RADAR_JSON}")


if __name__ == "__main__":
    main()
