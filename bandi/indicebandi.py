#!/usr/bin/env python3
"""Aggregatore bandi da IndiceBandi.it (categoria Terzo Settore).

Scorre le pagine HTML della categoria, poi arricchisce ogni bando
con la pagina singola per ente, scadenza, budget.

Output: data/bandi/indicebandi_bandi.json (stessa convenzione altre fonti).

Uso:
    python3 bandi/indicebandi.py          # cache se <1h
    python3 bandi/indicebandi.py --full    # forza refresh
"""

import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from config import filtra_bandi_attivi, normalizza_scadenza

CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "bandi"
CACHE_FILE = CACHE_DIR / "indicebandi_bandi.json"
BASE_URL = "https://www.indicebandi.it"
CAT_URL = "https://www.indicebandi.it/it/taxonomy/term/30"
HEADERS = {"User-Agent": "tsi/0.2 (+https://github.com/dataciviclab)", "Accept-Encoding": "gzip, deflate"}
CACHE_TTL = 3600


def fetch_bandi(force=False):
    if not force and CACHE_FILE.exists():
        age = time.time() - CACHE_FILE.stat().st_mtime
        if age < CACHE_TTL:
            with open(CACHE_FILE) as f:
                return json.load(f)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Passo 1: raccogli tutti gli URL dalla categoria paginata
    urls = _raccogli_url()
    print(f"📋 Trovati {len(urls)} bandi, scarico dettagli...", file=sys.stderr)

    # Passo 2: per ogni URL, fetcha la pagina singola
    bandi = []
    for i, u in enumerate(urls):
        b = _da_pagina_singola(u)
        if b:
            bandi.append(b)
        if (i + 1) % 5 == 0:
            print(f"   [{i+1}/{len(urls)}]", file=sys.stderr)
        time.sleep(0.3)

    bandi = filtra_bandi_attivi(bandi)

    with open(CACHE_FILE, "w") as f:
        json.dump(bandi, f, ensure_ascii=False, indent=2)

    return bandi


def _raccogli_url():
    """Scorre pagine della categoria e raccoglie URL."""
    visti = set()
    page = 0

    while True:
        url = CAT_URL if page == 0 else f"{CAT_URL}?page={page}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                break
            soup = BeautifulSoup(resp.text, "html.parser")
            links = soup.find_all("a", href=re.compile(r"^/it/bando/"))
            trovati = 0
            for a in links:
                href = BASE_URL + a["href"]
                titolo = a.get_text(strip=True)
                if href not in visti and titolo:
                    visti.add(href)
                    trovati += 1
            if trovati == 0:
                break
            page += 1
        except requests.RequestException:
            break

    return list(visti)


def _da_pagina_singola(url):
    """Estrae tutti i campi dalla pagina singola del bando."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return None
    except requests.RequestException:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    def campo(nc):
        d = soup.find("div", class_=re.compile(nc))
        if d:
            item = d.find(class_="field__item")
            if item:
                return item.get_text(strip=True)
        return ""

    def campi_multipli(nc):
        d = soup.find("div", class_=re.compile(nc))
        if d:
            return [it.get_text(strip=True) for it in d.find_all(class_="field__item")]
        return []

    titolo_tag = soup.find("h1")
    titolo = titolo_tag.get_text(strip=True) if titolo_tag else ""

    ente = campo("field-tipologia") or "?"
    apertura = campo("field-conferma-apertura")
    chiusura = campo("field-conferma-")
    descrizione = campo("field-cosa-finanzia")
    argomenti = campi_multipli("field-argomento")
    link_esterno = campo("field-accedi")

    scadenza = _parse_scadenza(chiusura or apertura)
    budget = _parse_budget(f"{titolo} {descrizione}")
    territorio = _inferisci_territorio(ente, titolo, descrizione or "")

    return {
        "titolo": titolo,
        "url": url,
        "ente": ente,
        "scadenza": scadenza,
        "budget": budget,
        "territorio": territorio,
        "tags": [a.strip().lower() for a in argomenti if a.strip()],
        "descrizione": (descrizione or "")[:2000],
        "link_esterno": link_esterno,
        "fonte": "indicebandi",
    }


# ── Helper ───────────────────────────────────────────────

_parse_scadenza = normalizza_scadenza


def _parse_budget(testo):
    if not testo:
        return None
    m = re.search(
        r"(?:budget|stanziamento|dotazione|importo|finanziamento|risorse|contributo)"
        r".{0,80}?"
        r"\s*([1-9]\d{0,2}(?:[.\s]\d{3})+)\s*(?:euro|€)?",
        testo, re.IGNORECASE | re.DOTALL
    )
    if m:
        try:
            return float(m.group(1).strip().replace(" ", "").replace(".", ""))
        except ValueError:
            pass
    return None


def _inferisci_territorio(ente, titolo, descrizione):
    testo = f"{ente} {titolo} {descrizione}".lower()
    if "nazionale" in testo or "italia" in testo:
        return "Nazionale"
    if any(w in testo for w in ["europa", "europea", "unione"]):
        return "Europa"
    mappa = [
        ("lombardia", "Lombardia"), ("veneto", "Veneto"), ("piemonte", "Piemonte"),
        ("liguria", "Liguria"), ("emilia", "Emilia-Romagna"), ("toscana", "Toscana"),
        ("lazio", "Lazio"), ("campania", "Campania"), ("puglia", "Puglia"),
        ("sicilia", "Sicilia"), ("sardegna", "Sardegna"), ("calabria", "Calabria"),
        ("friuli", "Friuli Venezia Giulia"), ("trentino", "Trentino Alto Adige"),
        ("marche", "Marche"), ("umbria", "Umbria"), ("abruzzo", "Abruzzo"),
        ("molise", "Molise"), ("basilicata", "Basilicata"),
    ]
    for kw, nome in mappa:
        if kw in testo:
            return nome
    return "Nazionale/da verificare"


if __name__ == "__main__":
    force = "--full" in sys.argv
    bandi = fetch_bandi(force=force)
    print(f"✅ {len(bandi)} bandi da IndiceBandi")

    enti = Counter(b["ente"] for b in bandi if b.get("ente") and b["ente"] != "?")
    print(f"\nEnti ({len(enti)}):")
    for e, c in enti.most_common(10):
        print(f"  · {e:40s} {c:>3d}")
    print(f"\nBudget: {sum(1 for b in bandi if b.get('budget'))}/{len(bandi)}")
    print(f"Scadenza: {sum(1 for b in bandi if b.get('scadenza'))}/{len(bandi)}")
    print(f"Cache: {CACHE_FILE}")
