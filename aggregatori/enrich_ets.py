"""OSINT enrichment ETS via Google Places API — CLI wrapper.

Prende una lista di ETS e per ognuno cerca su Google Places:
sito web, telefono, indirizzo, rating, categoria.

Uso:
    python aggregatori/enrich_ets.py --candidates MI    # provincia MI
    python aggregatori/enrich_ets.py --cf 90005350153   # specifico
"""

import json, sys, time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from lib.places import cerca_ets


def arricchisci_ets(ets_list: list[dict]) -> list[dict]:
    """Arricchisce una lista di ETS con dati Google Places."""    
    risultati = []
    for i, ets in enumerate(ets_list):
        cf = ets.get("codice_fiscale", "")
        denom = ets.get("denominazione", ets.get("nome", ""))
        comune = ets.get("comune", "")
        dati = cerca_ets(denom, comune)
        arricchito = {**ets, "enrich": dati}
        risultati.append(arricchito)
        if (i + 1) % 10 == 0:
            print(f"  ⌛ {i+1}/{len(ets_list)} ETS processati")
        time.sleep(0.2)
    return risultati


if __name__ == "__main__":
    con = duckdb.connect()
    ets_list = []

    if "--cf" in sys.argv:
        cf = sys.argv[sys.argv.index("--cf") + 1]
        r = con.sql(f"SELECT codice_fiscale, denominazione, comune, provincia, sezione, capacita_progettuale FROM 'data/unified_ets.parquet' WHERE codice_fiscale = '{cf}'").fetchdf()
        if r.empty:
            print(f"❌ ETS {cf} non trovato"); exit(1)
        ets_list = r.to_dict("records")

    elif "--candidates" in sys.argv:
        provincia = sys.argv[sys.argv.index("--candidates") + 1]
        r = con.sql(f"""
            SELECT codice_fiscale, denominazione, comune, provincia, sezione, capacita_progettuale,
                   cinque_2025, ha_grant_ue, ha_aiuti_stato
            FROM 'data/unified_ets.parquet'
            WHERE provincia = '{provincia}' AND capacita_progettuale IN ('medio-alta', 'alta')
            ORDER BY cinque_2025 DESC NULLS LAST LIMIT 20
        """).fetchdf()
        ets_list = r.to_dict("records")

    else:
        print("Uso: python aggregatori/enrich_ets.py --cf CF | --candidates MI")
        exit(1)

    print(f"📋 {len(ets_list)} ETS da arricchire")
    arricchiti = arricchisci_ets(ets_list)

    out = ROOT / "data" / "enriched_candidates.json"
    with open(out, "w") as f:
        json.dump(arricchiti, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Salvato: {out}")

    n = sum(1 for e in arricchiti if e.get("enrich"))
    print(f"\n✅ {n}/{len(arricchiti)} arricchiti")
