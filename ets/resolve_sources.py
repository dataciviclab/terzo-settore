#!/usr/bin/env python3
"""Risoluzione sorgenti per build_fatti_ets (driver-first).

Genera il SQL finale con i path già risolti, cercando nell'ordine:
  1. Layer clean locale del Lab:  ../dataset-incubator/out/data/clean/{slug}/{year}/{fname}
  2. Cache TSI valida:            data/gcs_cache/{fname}
  3. GCS (ultima spiaggia):       https://storage.googleapis.com/dataciviclab-clean/{slug}/{year}/{fname}

Uso:
    python3 ets/resolve_sources.py           # stampa la tabella di risoluzione
    python3 ets/resolve_sources.py --sql     # genera il SQL driver-first risolto
"""

import ast
import re
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
LAB = Path(__file__).resolve().parents[1].parent / "dataset-incubator" / "out" / "data" / "clean"
CACHE = ROOT / "data" / "gcs_cache"
GCS = "https://storage.googleapis.com/dataciviclab-clean"

# Stessa lista in ets/sources.py (fonte di verità delle dipendenze)
from sources import SOURCES


def parquet_valido(p: Path) -> bool:
    """Un parquet è valido se DuckDB lo legge. Connessione per file (no falsi positivi)."""
    try:
        con = duckdb.connect()
        con.sql(f"SELECT count(*) FROM '{p}'").fetchone()
        return True
    except Exception:
        return False
    finally:
        con.close()


def resolve(slug: str, year, fname: str) -> tuple[str, str]:
    """Ritorna (path_quotato, fonte) con fonte in {lab, cache, gcs}."""
    year = str(year)
    lab = LAB / slug / year / fname
    if lab.exists() and lab.stat().st_size > 0:
        return f"'{lab}'", "lab"
    cache = CACHE / fname
    if cache.exists() and cache.stat().st_size > 0 and parquet_valido(cache):
        return f"'{cache}'", "cache"
    return f"'{GCS}/{slug}/{year}/{fname}'", "gcs"


def tabella():
    print(f"{'slug':28s} {'anno':>5s} {'fonte':7s} path")
    for slug, year, fname in SOURCES:
        path, fonte = resolve(slug, year, fname)
        print(f"{slug:28s} {year:>5} {fonte:7s} {path}")


def build_sql() -> str:
    """Sostituisce i segnaposto {slug_year} nel template con i path risolti."""
    template = (ROOT / "ets" / "build_fatti_ets_driver.sql").read_text()
    for slug, year, fname in SOURCES:
        path, _ = resolve(slug, year, fname)
        template = template.replace(f"{{{slug}_{year}}}", path)
    # rimuove la macro p() ormai inutile e il suo utilizzo residuo
    template = re.sub(r"CREATE OR REPLACE MACRO p\(.*?\n\);\n", "", template, flags=re.DOTALL)
    return template


if __name__ == "__main__":
    if "--sql" in sys.argv:
        print(build_sql())
    else:
        tabella()
