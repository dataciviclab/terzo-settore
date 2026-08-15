#!/usr/bin/env python3
"""Pacchetto territorio — deliverable per i CSV (T1/T2).

Genera un pacchetto dati auto-contenuto per una provincia, pensato come
prodotto da consegnare a un Centro di Servizio per il Volontariato:
aggregati ETS + contesto sociale + bandi con match locale + gap.

Uso:
    python3 match/reports/pacchetto.py BO              # → data/reporting/territorio_BO.json
    python3 match/reports/pacchetto.py BO --markdown   # + territorio_BO.md
    python3 match/reports/pacchetto.py all             # tutti i TERRITORI_TARGET
"""

import argparse, json, sys
from datetime import datetime
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from match.reports.analytics import (
    contesto_sociale, ets_landscape, ets_riservati, ets_immobili, top_ets,
    gap_territoriale, vista_territorio,
)
from match.reports.render import markdown as md

ROOT = Path(__file__).resolve().parents[2]
REPORTING = ROOT / "data" / "reporting"

# Territori target (fase T1 pilota Bologna + T2 ER): configurare qui.
TERRITORI_TARGET = ["BO", "FC", "FE", "MO", "PC", "PR", "RA", "RE", "RN"]


def build_pacchetto(con, territorio):
    """Costruisce il pacchetto dati per una provincia (JSON-serializzabile)."""
    vista = vista_territorio(con, territorio)
    gap = gap_territoriale(con, provincia=territorio, limite=15)
    return {
        "schema": "territorio_pacchetto_v1",
        "territorio": territorio,
        "generato": datetime.now().isoformat(timespec="seconds"),
        "sorgenti": ["unified_ets", "comuni_ets", "unified_comuni", "inps_rdc_pdc", "infobandi", "info_cooperazione"],
        "ets": {
            "tot": vista["ets_landscape"]["tot"],
            "per_capacita": vista["ets_landscape"]["per_capacita"],
            "per_tipologia": vista["ets_landscape"]["per_tipologia"],
        },
        "contesto_sociale": vista["contesto"],
        "bandi_con_match_locale": vista["bandi_locali"],
        "top_ets": vista["top_ets"],
        "ets_appalti_riservati": vista["ets_riservati"],
        "ets_immobili_pubblici": vista["ets_immobili"],
        "gap_territoriali": gap,
    }


def genera(territorio, con_md=False):
    con = duckdb.connect()
    pacchetto = build_pacchetto(con, territorio)
    REPORTING.mkdir(parents=True, exist_ok=True)
    out_json = REPORTING / f"territorio_{territorio}.json"
    out_json.write_text(json.dumps(pacchetto, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Pacchetto: {out_json}")

    if con_md:
        out_md = REPORTING / f"territorio_{territorio}.md"
        out_md.write_text(md.render_segnale(vista_territorio(con, territorio)), encoding="utf-8")
        print(f"✅ Markdown:  {out_md}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Genera pacchetto territorio per CSV")
    parser.add_argument("territorio", help="Sigla provincia (es. BO) oppure 'all'")
    parser.add_argument("--markdown", action="store_true", help="Genera anche il .md")
    args = parser.parse_args(argv)

    if args.territorio.lower() == "all":
        for t in TERRITORI_TARGET:
            genera(t, con_md=args.markdown)
    else:
        genera(args.territorio.upper(), con_md=args.markdown)


if __name__ == "__main__":
    main()
