"""Aggregatore bandi da infobandi.csvnet.it (CSVNet).

Polling: REST API + RSS feed.
Output: JSON strutturato con ente, scadenza, budget, tag, link.

Uso diretto:
    python aggregatori/bandi/infobandi.py
    from aggregatori.bandi.infobandi import fetch_bandi, filtra_per_territorio
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from config import filtra_bandi_attivi, normalizza_scadenza

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "bandi"
CACHE_FILE = CACHE_DIR / "infobandi_bandi.json"
CACHE_TTL = 3600 

API_BASE = "https://infobandi.csvnet.it/wp-json/wp/v2"
RSS_URL = "https://infobandi.csvnet.it/feed/"
HEADERS = {"User-Agent": "terzo-settore-intelligence/0.1 (+https://github.com/dataciviclab)"}


def _gg_rimasti(scadenza: str, oggi: datetime | None = None) -> int | None:
    """Giorni fino alla scadenza (None se non parsabile)."""
    norm = normalizza_scadenza(scadenza)
    if not norm:
        return None
    oggi = oggi or datetime.now()
    try:
        scad = datetime.strptime(norm, "%Y-%m-%d")
        return (scad - oggi).days
    except ValueError:
        return None


def fmt_euro(valore: float | int | str | None) -> str:
    """Formatta un valore in euro leggibile."""
    if valore is None:
        return "N/D"
    try:
        v = float(valore)
    except (ValueError, TypeError):
        return str(valore)
    if v >= 1_000_000:
        return f"€{v / 1_000_000:,.2f}M".replace(",", ".")
    elif v >= 1_000:
        return f"€{v:,.0f}".replace(",", ".")
    else:
        return f"€{v:.2f}"





def fetch_bandi(force: bool = False) -> list[dict]:
    if not force and CACHE_FILE.exists():
        age = time.time() - CACHE_FILE.stat().st_mtime
        if age < CACHE_TTL:
            with open(CACHE_FILE) as f:
                return json.load(f)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    bandi = []
    page = 1

    while True:
        url = f"{API_BASE}/posts?per_page=100&page={page}&_fields=id,date,title,link,categories,tags,content"
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = json.loads(resp.content.decode("utf-8-sig"))

        if not data:
            break

        for post in data:
            bandi.append(_estrai(post))

        total = int(resp.headers.get("X-WP-Total", 0))
        if len(bandi) >= total:
            break
        page += 1
        time.sleep(0.3)

    bandi = filtra_bandi_attivi(bandi)

    with open(CACHE_FILE, "w") as f:
        json.dump(bandi, f, ensure_ascii=False, indent=2)

    return bandi


def _estrai(post: dict) -> dict:
    html = post.get("content", {}).get("rendered", "")

    ente = _campo(html, r"ENTE EROGATORE")
    scadenza = _campo(html, r"SCADENZA")
    obiettivi = _campo(html, "OBIETTIVI")
    ammissibili = _campo(html, "SOGGETTI AMMISSIBILI")
    tag_raw = re.findall(r'rel="tag">([^<]+)<', html)

    # Testo pulito per NLP
    testo = re.sub(r"<[^>]+>", " ", html)
    testo = re.sub(r"\s+", " ", testo).strip()

    # Budget: cerca importi con punti separatori vicino a keyword finanziarie
    budget = None
    pattern_budget = re.compile(
        r"(?:budget|stanziamento|dotazione|importo|finanziamento|risorse|plafond|contributo)"
        r"(?:\s+(?:complessiv[ao]|totale|massimo|previsto|stanziato|iniziale|disponibile|finale|richiesto|massimo))?"
        r"(?:\s+(?:complessiv[ao]|totale|massimo|previsto|stanziato|iniziale|disponibile|finale|richiesto|massimo))?"
        r"(?:[^e]{0,50})"
        r"(?:di|pari a|è di|fino a|massimo)"
        r"(?:\s*[€])?"
        r"\s*([\d]{1,3}(?:[.\s][\d]{3})+)\s*(?:[e][u][r][o]|€)?",
        re.IGNORECASE
    )
    m = pattern_budget.search(testo)
    if m:
        raw = m.group(1).strip().replace(' ', '').replace('.', '')
        try:
            budget = float(raw)
        except ValueError:
            budget = m.group(1)
    
    # Se non trovato, cerca pattern "X milioni di euro" 
    if not budget:
        m = re.search(
            r"(?:budget|stanziamento|dotazione|importo|finanziamento|totale|ammontare)"
            r"(?:[^e]{0,50})"
            r"(?:di|è di|pari a)"
            r"\s*([\d,]+)\s*(?:milioni?)\s*(?:di\s*)?(?:euro|€)",
            testo, re.IGNORECASE
        )
        if m:
            raw = m.group(1).strip().replace(',', '.')
            try:
                budget = float(raw) * 1_000_000
            except ValueError:
                pass

    return {
        "id": post["id"],
        "data": post["date"][:10],
        "titolo": post["title"]["rendered"],
        "url": post["link"],
        "categorie": post.get("categories", []),
        "ente_erogatore": ente,
        "scadenza": scadenza,
        "budget": budget,
        "obiettivi": obiettivi[:300] + "..." if obiettivi and len(obiettivi) > 300 else obiettivi,
        "ammissibili": ammissibili[:300] + "..." if ammissibili and len(ammissibili) > 300 else ammissibili,
        "testo_nlp": testo[:6000],
        "tag": tag_raw,
    }


def _campo(html: str, label: str) -> str | None:
    pattern = re.compile(
        rf"{label}\s*</strong></p>\s*<p[^>]*>(.*?)(?:</p>|<(?:ul|h|p\s))", re.DOTALL
    )
    m = pattern.search(html)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()[:500]
    return None


if __name__ == "__main__":
    bandi = fetch_bandi(force=True)
    print(f"Totale bandi: {len(bandi)}")
    # Calcola in scadenza
    oggi = datetime.now()
    in_scadenza = [b for b in bandi if b.get("scadenza") and _gg_rimasti(b["scadenza"], oggi) is not None and _gg_rimasti(b["scadenza"], oggi) <= 90]
    print(f"In scadenza (90gg): {len(in_scadenza)}")
    for b in sorted(in_scadenza, key=lambda x: x.get("scadenza", ""))[:5]:
        budget = fmt_euro(b.get("budget")) if b.get("budget") else "N/D"
        print(f"  · {b['scadenza']} | {b['titolo'][:60]}")
        print(f"    {b.get('ente_erogatore', '?')} — {budget}")
