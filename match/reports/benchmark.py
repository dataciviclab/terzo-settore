#!/usr/bin/env python3
"""Benchmark ETS × Lab — parquet con aggregati per livello nazionale/regione/provincia.

Genera la tabella per-ETS (data/reporting/ets_bandi.parquet) con il match
reale dei 53 bandi attivi (n_bandi_match senza cap), poi aggrega per livello:
quanti ETS hanno 1+ match col Lab e quanti 1+ match con bandi.

Output:
  data/reporting/ets_bandi.parquet     — una riga per ETS (150k)
  data/reporting/benchmark_ets.parquet — aggregati per livello (134 righe)
  data/reporting/benchmark_ets.csv     — idem CSV
"""

import json, sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "match"))

from lib.config import RADAR_REPORT
from match.pipeline import run_scan, load_bandi

LAB = ("(ha_5x1000 OR ha_appalti_pubblici OR ha_finanziamenti_ue OR ha_progetti_pnrr "
       "OR ha_aiuti_stato OR subappalti>0 OR patrimonio_immobili>0 OR ha_partecipato_gare)")

OUT_DIR = ROOT / "data" / "reporting"
ETS_BANDI = OUT_DIR / "ets_bandi.parquet"
BENCH = OUT_DIR / "benchmark_ets.parquet"
BENCH_CSV = BENCH.with_suffix(".csv")

# Cap alto per il conteggio reale degli idonei per bando (il radar usa 20
# per il rendering, qui serviamo la domanda vera senza cap).
IDONEI_CAP = 500_000


def genera_ets_bandi(con):
    """Calcola per ogni CF ETS quanti dei bandi attivi matcha (senza cap)."""
    scan = run_scan(con=con, bandi=load_bandi(), match_limit=IDONEI_CAP)
    from collections import defaultdict
    ets_bandi = defaultdict(set)
    for r in scan["resultados"]:
        for c in r["candidati"]:
            cf = c.get("codice_fiscale") or c.get("cf")
            if cf:
                ets_bandi[cf].add(r["titolo"])

    con.sql("CREATE TEMP TABLE ets_bandi (codice_fiscale VARCHAR, n_bandi INT)")
    con.sql("INSERT INTO ets_bandi SELECT * FROM (VALUES "
            + ",".join(f"('{cf}',{len(set)})" for cf, set in ets_bandi.items()) + ")")

    df = con.sql("""
        SELECT e.codice_fiscale, e.denominazione, e.sezione, e.comune,
               e.provincia, e.regione, e.capacita_progettuale,
               COALESCE(b.n_bandi, 0) as n_bandi_match,
               e.ha_5x1000, e.ha_appalti_pubblici, e.ha_finanziamenti_ue,
               e.ha_progetti_pnrr, e.ha_aiuti_stato, e.ha_partecipato_gare,
               e.subappalti, e.patrimonio_immobili,
               e.importo_5x1000_2025
        FROM 'data/unified_ets.parquet' e
        LEFT JOIN ets_bandi b ON e.codice_fiscale = b.codice_fiscale
    """).fetchdf()
    df.to_parquet(ETS_BANDI, index=False)
    return df


def aggrega(con, livello):
    group_by = "" if livello == "nazionale" else " GROUP BY 1"
    return con.sql(f"""
        SELECT {'NULL' if livello=='nazionale' else f'COALESCE({livello},\'?\')'} as gruppo,
               COUNT(*) n_ets,
               COUNT(*) FILTER (WHERE {LAB}) n_lab,
               COUNT(*) FILTER (WHERE n_bandi_match > 0) n_bando,
               COUNT(*) FILTER (WHERE ha_5x1000) n_5x1000,
               COUNT(*) FILTER (WHERE ha_appalti_pubblici) n_appalti,
               COUNT(*) FILTER (WHERE ha_finanziamenti_ue) n_ue,
               COUNT(*) FILTER (WHERE ha_progetti_pnrr) n_pnrr,
               COUNT(*) FILTER (WHERE ha_aiuti_stato) n_aiuti,
               COUNT(*) FILTER (WHERE ha_partecipato_gare) n_gare,
               COUNT(*) FILTER (WHERE patrimonio_immobili>0) n_immobili,
               COUNT(*) FILTER (WHERE subappalti>0) n_subappalti,
               ROUND(AVG(n_bandi_match), 1) avg_bandi
        FROM '{ETS_BANDI}'{group_by}
    """).fetchdf()


def main(argv=None):
    con = duckdb.connect()
    genera_ets_bandi(con)

    frames = []
    for livello, label in (("nazionale", "ITALIA"), ("regione", None), ("provincia", None)):
        df = aggrega(con, livello)
        df["livello"] = livello
        df["gruppo"] = label if label else df["gruppo"]
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df = df[["livello", "gruppo", "n_ets", "n_lab", "n_bando", "avg_bandi",
             "n_5x1000", "n_appalti", "n_ue", "n_pnrr", "n_aiuti", "n_gare",
             "n_immobili", "n_subappalti"]]
    df["pct_lab"] = (df["n_lab"] / df["n_ets"] * 100).round(1)
    df["pct_bando"] = (df["n_bando"] / df["n_ets"] * 100).round(3)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(BENCH, index=False)
    df.to_csv(BENCH_CSV, index=False)
    print(f"✅ ETS per bando: {ETS_BANDI}")
    print(f"✅ Benchmark:     {BENCH} ({len(df)} righe)")
    print(f"✅ CSV:           {BENCH_CSV}")

    n = df[df["livello"] == "nazionale"].iloc[0]
    print()
    print(f"Nazionale: {n['n_ets']:,} ETS RUNTS | {n['n_lab']:,} con 1+ match Lab ({n['pct_lab']}%) "
          f"| {n['n_bando']:,} con 1+ match bando ({n['pct_bando']}%) | media {n['avg_bandi']} bandi")


if __name__ == "__main__":
    main()
