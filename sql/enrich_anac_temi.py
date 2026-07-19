#!/usr/bin/env python3
"""Arricchisce unified_ets con temi ANAC dagli oggetti dei bandi partecipati.

Legge Partecipanti + Bandi Gara da GCS, estrae temi (minori, educazione, salute...)
dagli oggetti dei bandi a cui ogni ETS ha partecipato, e li salva in unified_ets.

Uso:
    python3 sql/enrich_anac_temi.py
    # Dopo make build
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))

from lib.patterns import TEXT_KEYWORDS

GCS = "https://storage.googleapis.com/dataciviclab-clean"
ETS_FILE = str(ROOT / "data/unified_ets.parquet")

PART_URL = f"{GCS}/anac_partecipanti/2026/anac_partecipanti_2026_clean.parquet"
BANDI_URL = f"{GCS}/anac_bandi_gara/2025/anac_bandi_gara_2025_clean.parquet"


from lib.temi import estrai_temi


def main():
    print("📥 Carico ETS...")
    con = duckdb.connect()

    # CF di tutti gli ETS
    ets_cf = con.sql(f"SELECT codice_fiscale FROM '{ETS_FILE}'").fetchdf()
    print(f"   {len(ets_cf)} ETS")

    # Crea tabella temporanea con i CF ETS per filtro
    con.sql("CREATE TEMP TABLE ets_cf AS SELECT * FROM ets_cf")

    # Join Partecipanti + Bandi Gara, filtrato per ETS
    print("📥 Join Partecipanti + Bandi Gara (solo ETS)...")
    df = con.sql(f"""
        SELECT p.codice_fiscale, b.oggetto_lotto, b.importo_lotto,
               b.oggetto_principale_contratto
        FROM read_parquet('{PART_URL}', union_by_name=true) p
        INNER JOIN read_parquet('{BANDI_URL}', union_by_name=true) b
            ON p.cig = b.cig
        INNER JOIN ets_cf e ON p.codice_fiscale = e.codice_fiscale
        WHERE b.oggetto_lotto IS NOT NULL
          AND b.oggetto_lotto != ''
    """).fetchdf()
    con.close()

    print(f"   {len(df)} partecipazioni ETS con oggetto")

    # NLP: estrai temi da ogni oggetto, aggrega per CF
    print("🧠 NLP sugli oggetti...")
    temi_per_cf: dict[str, set[str]] = defaultdict(set)

    for _, row in df.iterrows():
        cf = row["codice_fiscale"]
        oggetto = str(row["oggetto_lotto"] or "") + " " + str(row.get("oggetto_principale_contratto") or "")
        temi = estrai_temi(oggetto)
        if temi:
            temi_per_cf[cf].update(temi)

    print(f"   {len(temi_per_cf)} ETS con temi estratti")

    # Statistiche
    from collections import Counter
    tema_counter: Counter = Counter()
    for temi in temi_per_cf.values():
        for t in temi:
            tema_counter[t] += 1

    print(f"\n📊 Temi ANAC più frequenti ({len(tema_counter)} unici):")
    for tema, count in tema_counter.most_common(15):
        print(f"   · {tema:25s} {count:>5d} ETS")

    # Salva mapping CF → temi
    output = []
    for cf, temi in temi_per_cf.items():
        output.append({"codice_fiscale": cf, "temi_anac": ",".join(sorted(temi))})

    import pandas as pd
    df_temi = pd.DataFrame(output)

    print(f"\n💾 Salvo {len(df_temi)} righe in unified_ets...")

    # Leggi unified_ets esistente, aggiungi colonna temi_anac
    con2 = duckdb.connect()
    df_ets = con2.sql(f"SELECT * FROM '{ETS_FILE}'").fetchdf()
    con2.close()

    # Merge: aggiungi temi_anac
    df_ets = df_ets.merge(df_temi, on="codice_fiscale", how="left")
    df_ets["temi_anac"] = df_ets["temi_anac"].fillna("")

    # Salva
    df_ets.to_parquet(ETS_FILE, index=False)
    print(f"✅ {len(df_ets)} ETS salvati in {ETS_FILE}")
    print(f"   {len(temi_per_cf)} ETS con temi ANAC arricchiti")


if __name__ == "__main__":
    main()
