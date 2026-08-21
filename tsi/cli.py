"""CLI unica di Terzo Settore Intelligence.

Entry point: ``python3 -m tsi <comando> [args]``

Comandi:
    scheda-ente  — profilo ETS on-demand (query live, dati freschi)
    scheda-bando — profilo bando + ETS compatibili
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

COMMANDS = {
    "scheda-ente": ("reports.scheda_ente", "scheda ETS on-demand (query live, dati freschi)"),
    "scheda-bando": ("reports.scheda_bando", "profilo bando + ETS compatibili"),
    "vista-territorio": ("reports.vista_territorio", "panorama ETS di un comune/provincia/regione"),
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
