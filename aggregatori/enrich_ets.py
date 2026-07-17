"""OSINT enrichment ETS via Google Places API.

Prende una lista di ETS (da scan o da unified_ets) e per ognuno cerca
su Google Places: sito web, telefono, indirizzo, rating, categoria.

Uso:
    python aggregatori/enrich_ets.py --candidates MI    # provincia MI
    python aggregatori/enrich_ets.py --scan bper        # ultimo scan
    python aggregatori/enrich_ets.py --cf 90005350153   # specifico
"""

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
if not API_KEY:
    print("❌ SERVIRE GOOGLE_MAPS_API_KEY in .env")
    print("   Vai su https://console.cloud.google.com/ → API → Places API")
    exit(1)

CACHE_DIR = ROOT / "data" / "enrich"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

PLACES_TEXT_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAIL_URL = "https://maps.googleapis.com/maps/api/place/details/json"


def cerca_ets(denominazione: str, comune: str = "") -> dict | None:
    """Cerca un ETS su Google Places e torna dati arricchiti, o None."""
    # Cache su CF (passato come chiave esterna)
    query = f"{denominazione} {comune}".strip()

    cache_file = CACHE_DIR / f"{query[:50].replace('/', '_').replace(' ', '_')}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())

    resp = requests.get(PLACES_TEXT_URL, params={
        "query": query,
        "key": API_KEY,
        "language": "it",
        "region": "it",
    }, timeout=15)

    if resp.status_code != 200:
        return None

    data = resp.json()
    if data.get("status") != "OK" or not data.get("results"):
        return None

    place = data["results"][0]
    place_id = place.get("place_id", "")

    # Dettagli se abbiamo place_id
    dettagli = {}
    if place_id:
        time.sleep(0.1)
        dett_resp = requests.get(PLACES_DETAIL_URL, params={
            "place_id": place_id,
            "fields": "website,formatted_phone_number,rating,user_ratings_total,types,editorial_summary",
            "key": API_KEY,
            "language": "it",
        }, timeout=15)
        if dett_resp.status_code == 200:
            dett_data = dett_resp.json()
            if dett_data.get("status") == "OK":
                dettagli = dett_data.get("result", {})

    result = {
        "place_id": place_id,
        "nome_google": place.get("name"),
        "indirizzo": place.get("formatted_address"),
        "lat": place.get("geometry", {}).get("location", {}).get("lat"),
        "lng": place.get("geometry", {}).get("location", {}).get("lng"),
        "categorie_google": place.get("types", []),
        "sito_web": dettagli.get("website"),
        "telefono": dettagli.get("formatted_phone_number"),
        "rating": dettagli.get("rating"),
        "totale_recensioni": dettagli.get("user_ratings_total"),
        "icona": place.get("icon"),
    }

    cache_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def arricchisci_ets(ets_list: list[dict]) -> list[dict]:
    """Arricchisce una lista di ETS con dati Google Places."""
    risultati = []
    for i, ets in enumerate(ets_list):
        cf = ets.get("codice_fiscale", "")
        denom = ets.get("denominazione", ets.get("nome", ""))
        comune = ets.get("comune", "")

        # Check cache
        cache_hit = CACHE_DIR / f"{cf}.json"
        if cache_hit.exists():
            dati = json.loads(cache_hit.read_text())
        else:
            dati = cerca_ets(denom, comune)
            if dati:
                cache_hit.write_text(json.dumps(dati, ensure_ascii=False, indent=2))

        arricchito = {**ets, "enrich": dati}
        risultati.append(arricchito)

        if (i + 1) % 10 == 0:
            print(f"  ⌛ {i+1}/{len(ets_list)} ETS processati")

        time.sleep(0.2)  # rate limiting

    return risultati


if __name__ == "__main__":
    import sys
    import duckdb

    con = duckdb.connect()
    ets_list = []

    if "--cf" in sys.argv:
        cf = sys.argv[sys.argv.index("--cf") + 1]
        r = con.sql(f"SELECT codice_fiscale, denominazione, comune, provincia, sezione, capacita_progettuale FROM 'data/unified_ets.parquet' WHERE codice_fiscale = '{cf}'").fetchdf()
        if r.empty:
            print(f"❌ ETS {cf} non trovato")
            exit(1)
        ets_list = r.to_dict("records")
        print(f"🔍 Arricchisco {cf}...")

    elif "--candidates" in sys.argv:
        provincia = sys.argv[sys.argv.index("--candidates") + 1]
        print(f"🔍 Arricchisco ETS con capacità in provincia {provincia}...")
        r = con.sql(f"""
            SELECT codice_fiscale, denominazione, comune, provincia, sezione, capacita_progettuale,
                   cinque_2025, ha_grant_ue, ha_aiuti_stato
            FROM 'data/unified_ets.parquet'
            WHERE provincia = '{provincia}' AND capacita_progettuale IN ('medio-alta', 'alta')
            ORDER BY cinque_2025 DESC NULLS LAST
            LIMIT 20
        """).fetchdf()
        ets_list = r.to_dict("records")

    elif "--scan" in sys.argv:
        scan = sys.argv[sys.argv.index("--scan") + 1]
        # Legge candidati dal report ultimo scan
        print(f"🔍 Arricchisco candidati scan {scan}...")

    else:
        print("Uso: python aggregatori/enrich_ets.py --cf CF | --candidates MI | --scan bper")
        exit(1)

    if not ets_list:
        print("❌ Nessun ETS da processare")
        exit(1)

    print(f"📋 {len(ets_list)} ETS da arricchire")
    arricchiti = arricchisci_ets(ets_list)

    # Salva
    out = ROOT / "data" / "enriched_candidates.json"
    with open(out, "w") as f:
        json.dump(arricchiti, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Salvato: {out}")

    # Stampa riepilogo
    print(f"\n📊 Riepilogo enrichment:")
    con_enrich = 0
    for e in arricchiti:
        if e.get("enrich"):
            con_enrich += 1
            print(f"  ✅ {e['denominazione'][:50]}")
            print(f"     Sito: {e['enrich'].get('sito_web', '❌')}")
            print(f"     Tel: {e['enrich'].get('telefono', '❌')}")
            print(f"     Rating: {e['enrich'].get('rating', '❌')}")
        else:
            print(f"  ❌ {e['denominazione'][:50]} — non trovato su Google Places")
    print(f"\nTrovati: {con_enrich}/{len(arricchiti)}")
