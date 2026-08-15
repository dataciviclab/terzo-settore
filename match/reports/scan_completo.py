#!/usr/bin/env python3
"""Scan e report: orchestratore sottile (analytics → render → I/O).

Usage:
    python match/reports/scan_completo.py              # scan + radar-completo.json + .md
    python match/reports/scan_completo.py --latest     # bandi ≤60gg → radar-latest.md/json
    python match/reports/scan_completo.py --territorio MI [--comune X]  # segnale-MI.md/json
"""

import argparse, json, sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))

from lib.config import RADAR_REPORT
from match.pipeline import run_scan

from match.reports.analytics import vista_latest, vista_territorio, load_scan_local, gap_territoriale
from match.reports.render import markdown as md, json as js

ROOT = Path(__file__).resolve().parents[2]
RADAR_JSON = RADAR_REPORT.with_suffix(".json")
CRUSCOTTO = ROOT / "cruscotto"


def load_scan():
    if not RADAR_JSON.exists():
        print(f"❌ {RADAR_JSON} non trovato. Esegui scan_completo.py senza flag.")
        sys.exit(1)
    with open(RADAR_JSON) as f:
        return json.load(f)


def run_scan_completo():
    scan = run_scan()
    report_md = md.render_completo(scan)
    RADAR_REPORT.write_text(report_md, encoding="utf-8")
    print(f"✅ Markdown: {RADAR_REPORT}")

    report_json = js.completo(scan)
    RADAR_JSON.write_text(json.dumps(report_json, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ JSON:      {RADAR_JSON}")


def run_latest(giorni=60, territorio=None):
    scan = load_scan()
    con = duckdb.connect()
    vista = vista_latest(scan, con, giorni=giorni, territorio=territorio)

    out_md = CRUSCOTTO / "radar-latest.md"
    out_md.write_text(md.render_latest(vista), encoding="utf-8")
    print(f"✅ Markdown: {out_md}")

    out_json = CRUSCOTTO / "radar-latest.json"
    out_json.write_text(json.dumps(js.latest(vista), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ JSON:      {out_json}")


def run_territorio(territorio, comune=None):
    scan = load_scan()
    con = duckdb.connect()
    vista = vista_territorio(con, territorio, comune)

    titolo = (comune or territorio).lower()
    out_md = CRUSCOTTO / f"segnale-{titolo}.md"
    out_md.write_text(md.render_segnale(vista), encoding="utf-8")
    print(f"✅ Markdown: {out_md}")

    out_json = CRUSCOTTO / f"segnale-{titolo}.json"
    out_json.write_text(json.dumps(js.segnale(vista), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ JSON:      {out_json}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Scan bandi e report")
    parser.add_argument("--latest", action="store_true", help="Bandi ≤60gg → radar-latest.md")
    parser.add_argument("--territorio", help="Provincia (es. MI) → segnale-{T}.md")
    parser.add_argument("--comune", help="Comune (opzionale, con --territorio)")
    parser.add_argument("--giorni", type=int, default=60, help="Giorni per --latest (default 60)")
    args = parser.parse_args(argv)

    if args.latest:
        run_latest(giorni=args.giorni, territorio=args.territorio)
    elif args.territorio:
        run_territorio(args.territorio.upper(), args.comune)
    else:
        run_scan_completo()


if __name__ == "__main__":
    main()
