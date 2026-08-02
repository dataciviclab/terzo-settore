#!/usr/bin/env python3
"""Incrocio territoriale: match ETS × contesto comune.

Uso:
    python3 match/reports/incrocio.py --tags sport minori --terr Lombardia
    python3 match/reports/incrocio.py --tags disabilità --terr Mezzogiorno --out cruscotto/incrocio.md
"""

import argparse
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))

from match.funnel import format_incrocio, match_territoriale


def main():
    parser = argparse.ArgumentParser(description="Incrocio territoriale ETS × contesto")
    parser.add_argument("--tags", nargs="+", required=True, help="Tag tematici (es. sport minori)")
    parser.add_argument("--terr", nargs="+", default=None, help="Territorio (es. Lombardia, Mezzogiorno)")
    parser.add_argument("--limit", type=int, default=200, help="Max ETS matchati")
    parser.add_argument("--out", default=None, help="File output markdown (default: stdout)")
    args = parser.parse_args()

    con = duckdb.connect()
    match_ctx, gap = match_territoriale(con, args.tags, limit=args.limit, territorio=args.terr)
    titolo = "Incrocio: " + ", ".join(args.tags)
    if args.terr:
        titolo += " — " + ", ".join(args.terr)
    report = format_incrocio(match_ctx, gap, titolo=titolo)

    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"✅ Report salvato in {args.out}")
    else:
        print(report)


if __name__ == "__main__":
    main()
