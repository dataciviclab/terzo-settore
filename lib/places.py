"""Google Places enrichment for ETS entities."""

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from lab_connectors.http import HttpClient

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

CACHE_DIR = ROOT / "data" / "enrich"
PLACES_TEXT_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAIL_URL = "https://maps.googleapis.com/maps/api/place/details/json"

# HTTP client condiviso del Lab: retry, backoff, SSL fallback (lab-connectors)
_client = HttpClient(timeout=15)


def cerca_ets(denominazione: str, comune: str = "") -> dict | None:
    """Cerca un ETS su Google Places e torna dati arricchiti, o None."""
    if not API_KEY:
        return None

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    query = f"{denominazione} {comune}".strip()
    cache_file = CACHE_DIR / f"{query[:50].replace('/', '_').replace(' ', '_')}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())

    result = _client.get(PLACES_TEXT_URL, params={
        "query": query, "key": API_KEY, "language": "it", "region": "it",
    })
    if not result.is_ok or result.response is None:
        return None

    data = result.response.json()
    if data.get("status") != "OK" or not data.get("results"):
        return None

    place = data["results"][0]
    place_id = place.get("place_id", "")

    dettagli = {}
    if place_id:
        time.sleep(0.1)
        dett_result = _client.get(PLACES_DETAIL_URL, params={
            "place_id": place_id,
            "fields": "website,formatted_phone_number,rating,user_ratings_total,types,editorial_summary",
            "key": API_KEY, "language": "it",
        })
        if dett_result.is_ok and dett_result.response is not None:
            dett_data = dett_result.response.json()
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
    }

    cache_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result
