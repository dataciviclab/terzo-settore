#!/usr/bin/env python3
"""Aggregatore bandi da info-cooperazione.it.

Scarica tutti i bandi dalla sezione Bandi (Cat=2) paginata.
Cache locale: data/bandi/info_cooperazione_bandi.json
"""

import json, re, time, sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urljoin, parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data" / "bandi"
from lib.config import filtra_bandi_attivi, parse_scadenza

BASE_URL = "https://www.info-cooperazione.it"
SEARCH_URL = f"{BASE_URL}/Category/Search"
CACHE_FILE = CACHE_DIR / "info_cooperazione_bandi.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}

def fetch_page(page=1, donatore_id="", retries=2):
    params = {
        "Cat": "2",
        "donatore_id": donatore_id,
        "orderby": "Data scadenza",
        "nonscaduti": "false",
        "s": "",
        "page": str(page),
    }
    for attempt in range(retries + 1):
        try:
            r = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            if attempt < retries:
                print(f"⚠️  Timeout pagina {page}, riprovo ({attempt+1}/{retries})...", file=sys.stderr)
                time.sleep(2)
            else:
                print(f"❌  Pagina {page} non disponibile: {e}", file=sys.stderr)
                return ""

def parse_bandi(html):
    soup = BeautifulSoup(html, "html.parser")
    bandi = []
    for block in soup.select("div.post-block-wrapper.post-list-view"):
        title_el = block.select_one("h2.post-title a")
        if not title_el:
            continue
        url_rel = title_el.get("href", "")
        url = urljoin(BASE_URL, url_rel) if url_rel else ""
        titolo = title_el.get_text(strip=True)

        desc_el = block.select_one("div.righe-4")
        descrizione = desc_el.get_text(strip=True) if desc_el else ""

        scad_el = block.select_one(".text-danger strong")
        scadenza = ""
        if scad_el:
            raw = scad_el.get_text(strip=True)
            m = re.search(r"(\d{1,2}\s+\w+\s+\d{4})", raw)
            if m:
                scadenza = m.group(1)
            else:
                scadenza = raw.replace("Scadenza:", "").strip()

        donatore_el = block.select_one(".text-md-end small, .text-end small")
        donatore = ""
        if donatore_el:
            raw = donatore_el.get_text(strip=True)
            donatore = raw.replace("Donatore:", "").strip()

        # extract thumbnail for category hints
        img_el = block.select_one("img.img-120")
        img_url = urljoin(BASE_URL, img_el.get("src", "")) if img_el else ""

        # scaduto?
        scaduto = False
        if scadenza:
            d = parse_scadenza(scadenza)
            scaduto = d is not None and d < date.today()

        bandi.append({
            "titolo": titolo,
            "url": url,
            "descrizione": descrizione,
            "scadenza": scadenza,
            "scaduto": scaduto,
            "donatore": donatore,
            "img": img_url,
        })
    return bandi

def parse_pagination(html):
    soup = BeautifulSoup(html, "html.parser")
    links = soup.select("nav.pagination-wrapper a.page-link")
    pages = set()
    for a in links:
        href = a.get("href", "")
        qs = parse_qs(urlparse(href).query)
        p = qs.get("page", [None])[0]
        if p and p.isdigit():
            pages.add(int(p))
    # also check active page
    active = soup.select_one("nav.pagination-wrapper span.page-link")
    if active:
        txt = active.get_text(strip=True)
        if txt.isdigit():
            pages.add(int(txt))
    return max(pages) if pages else 1

def parse_detail(html):
    soup = BeautifulSoup(html, "html.parser")
    extra = {}

    # Budget: cerca pattern come €XX, € XXX (primo numero dopo "budget")
    testo = soup.get_text()
    m_budget = re.search(r"budget[:\s]*[e€]\s*([\d\.]+(?:,\d+)?)", testo, re.IGNORECASE)
    if m_budget:
        extra["budget"] = m_budget.group(1)

    # Territorio: cerca "Mezzogiorno", "nazionale", "regionale"
    for kw in ["Mezzogiorno", "nazionale", "regionale", "locale", "Europa"]:
        if kw.lower() in testo.lower():
            extra.setdefault("territorio", []).append(kw)

    # Tag/parole chiave dalla descrizione
    parole_chiave = ["disabilità", "sport", "cultura", "ambiente", "giovani",
                     "minori", "donne", "migranti", "salute", "lavoro", "educazione",
                     "digitale", "ricerca", "volontariato", "inclusione"]
    found_tags = [p for p in parole_chiave if p.lower() in testo.lower()]
    if found_tags:
        extra["tags"] = found_tags

    return extra

def fetch_detail(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return parse_detail(r.text)
    except Exception as e:
        print(f"  ⚠️  Errore detail {url[:60]}: {e}", file=sys.stderr)
        return {}

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Scarica TUTTI i bandi storici")
    parser.add_argument("--max-pages", type=int, default=10,
                        help="Max pagine (default: 10 = ~200 bandi). Usa --full per tutti.")
    args = parser.parse_args()

    print("🔍 Scraping info-cooperazione.it bandi...")
    tutti = []
    page = 1
    max_pages = args.max_pages if not args.full else 999

    while page <= max_pages:
        print(f"  Pagina {page}...", end=" ", flush=True)
        html = fetch_page(page=page)
        bandi = parse_bandi(html)
        print(f"{len(bandi)} bandi trovati")
        if not bandi:
            print("  (pagina vuota — stop)")
            break
        tutti.extend(bandi)
        page += 1
        time.sleep(0.5)

    # Fetch dettagli per bandi non scaduti (per i match)
    da_dettagliare = [b for b in tutti if not b.get("scaduto")]
    print(f"\n📄 Fetch dettagli per {len(da_dettagliare)}/{len(tutti)} bandi non scaduti...")
    for i, b in enumerate(da_dettagliare):
        if b["url"]:
            extra = fetch_detail(b["url"])
            b.update(extra)
        if (i + 1) % 5 == 0:
            print(f"  {i+1}/{len(da_dettagliare)}")

    # Salva cache
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tutti = filtra_bandi_attivi(tutti)
    data = {
        "fonte": "info-cooperazione.it",
        "scraped_at": datetime.now().isoformat(),
        "totale": len(tutti),
        "bandi": tutti,
    }
    CACHE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"\n✅ Salvati {len(tutti)} bandi in {CACHE_FILE}")

    # Stats
    donatori = set(b["donatore"] for b in tutti if b["donatore"])
    print(f"\n📊 Statistiche:")
    print(f"  Bandi totali: {len(tutti)}")
    print(f"  Donatori unici: {len(donatori)}")
    print(f"  Top donatori:")
    for don, cnt in Counter(b["donatore"] for b in tutti if b["donatore"]).most_common(10):
        print(f"    · {don}: {cnt}")

if __name__ == "__main__":
    main()
