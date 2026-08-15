"""CLI unica di Terzo Settore Intelligence.

Entry point: ``python3 -m tsi <comando> [args]``

I comandi delegano ai moduli di ``match/reports/`` (logica invariata);
qui vivono solo il dispatch e la configurazione dei path.

Comandi:
    scan       — scan bandi + radar-completo (markdown+json)
    contatta   — esporta candidati da contattare per un bando
    scheda     — profilo ETS (base/ANAC/match/benchmark)
    pacchetto  — deliverable territorio per i CSV (T1/T2)
    benchmark  — aggregati ETS × Lab per livello
    incrocio   — match ETS × contesto comune
    outreach   — kit di scoperta per pilota outreach
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))

COMMANDS = {
    "scan": ("match.reports.scan_completo", "scan bandi + radar-completo (markdown+json)"),
    "contatta": ("match.reports.contatta", "esporta candidati da contattare per un bando"),
    "scheda": ("match.reports.scheda", "profilo ETS (base/ANAC/match/benchmark)"),
    "pacchetto": ("match.reports.pacchetto", "deliverable territorio per i CSV (T1/T2)"),
    "benchmark": ("match.reports.benchmark", "aggregati ETS × Lab per livello"),
    "incrocio": ("match.reports.incrocio", "match ETS × contesto comune"),
    "outreach": ("match.reports.outreach", "kit di scoperta per pilota outreach"),
}


def _help() -> str:
    lines = ["Uso: python3 -m tsi <comando> [args]", "", "Comandi:"]
    for name, (_, desc) in COMMANDS.items():
        lines.append(f"  {name:10s} {desc}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv or argv[0] in ("-h", "--help", "help"):
        print(_help())
        return 0

    cmd = argv.pop(0)
    if cmd not in COMMANDS:
        print(f"Comando sconosciuto: {cmd}\n")
        print(_help())
        return 2

    module = importlib.import_module(COMMANDS[cmd][0])
    return int(module.main(argv) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
