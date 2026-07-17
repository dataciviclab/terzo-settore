"""HTML fallback: estrae dati da pagine bando quando API/listing non bastano."""

import re
import requests
from bs4 import BeautifulSoup


_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html",
    "Accept-Language": "it-IT,it;q=0.9",
}


_CONTENT_SELECTORS = [
    "div.et_pb_post_content",
    "div.entry-content",
    "div.post-content",
    "article",
    "main",
    "body",
]


def fetch_text(url: str, timeout: int = 15) -> str | None:
    """Scarica HTML e restituisce testo leggibile (salta nav, header, footer)."""
    try:
        r = requests.get(url, headers=_HEADERS, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Rimuovi boilerplate
        for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        # Cerca il contenuto principale
        for selector in _CONTENT_SELECTORS:
            container = soup.select_one(selector)
            if container and len(container.get_text(strip=True)) > 200:
                return container.get_text(separator=" ", strip=True)

        # Fallback: tutto il body
        body = soup.find("body")
        return body.get_text(separator=" ", strip=True) if body else None

    except Exception as e:
        return None


# Pattern per estrazione
# Match: "dotazione di € 2.250.000" oppure "dotazione di 2.250.000 euro"
# Pattern: keyword + numero con punti separatori (es. "dotazione di 2.250.000")
_RE_BUDGET_KEYWORD = re.compile(
    r'(?:budget|stanziamento|dotazione|importo|finanziamento|risorse)'
    r'(?:\s+(?:complessiv[ao]|totale|massimo|previsto|disponibile|stanziato))?'
    r'(?:\s+di)?'
    r'(?:\s*[€£\$])?'
    r'\s*([\d]{1,3}(?:[.\s][\d]{3})+(?:[.,]\d{1,2})?)',
    re.IGNORECASE,
)
# Pattern: keyword + numero + "euro" (es. "dotazione di 2.250.000 euro")
_RE_BUDGET_KEYWORD_POST = re.compile(
    r'(?:budget|stanziamento|dotazione|importo|finanziamento|risorse)'
    r'(?:\s+(?:complessiv[ao]|totale|massimo|previsto|disponibile|stanziato))?'
    r'(?:\s+di)?'
    r'\s*([\d]{1,3}(?:[.\s][\d]{3})+(?:[.,]\d{1,2})?)'
    r'\s*(?:e[ur]|€|£|\$)',
    re.IGNORECASE,
)
# Pattern generico: € X.XXX
_RE_BUDGET_NUM = re.compile(r'[€£$]\s*([\d]{1,3}(?:[.\s][\d]{3})+(?:[.,]\d{1,2})?)')


def extract_budget(text: str) -> float | None:
    """Cerca importo budget nel testo."""
    for pattern in (_RE_BUDGET_KEYWORD, _RE_BUDGET_KEYWORD_POST, _RE_BUDGET_NUM):
        m = pattern.search(text)
        if m:
            raw = m.group(1).strip().replace(' ', '').replace('.', '').replace(',', '.')
            try:
                val = float(raw)
                if val > 100:  # soglia minima per evitare falsi positivi
                    return val
            except ValueError:
                pass
    return None


_TERRITORIO_PATTERNS = {
    "mezzogiorno": ["mezzogiorno", "sud", "meridione"],
    "nazionale": ["nazionale", "tutta italia", "italiano"],
    "europa": ["europa", "europeo", "ue", "unione europea"],
    "regionale": ["regionale", "regione"],
}


def extract_territory(text: str) -> list[str]:
    """Individua aree geografiche menzionate."""
    lower = text.lower()
    found = set()
    for area, keywords in _TERRITORIO_PATTERNS.items():
        if any(kw in lower for kw in keywords):
            found.add(area)
    return sorted(found)


def arricchisci(url: str | None, testo_esistente: str | None = None) -> dict:
    """Fallback: scarica pagina, estrae budget + territorio + testo NLP."""
    if not url:
        return {}

    html_text = fetch_text(url)
    if not html_text:
        return {}

    result = {}

    # Budget
    budget = extract_budget(html_text)
    if budget:
        result["budget"] = budget

    # Territorio
    terr = extract_territory(html_text)
    if terr:
        result["territorio"] = terr

    # Testo per NLP (se non già presente)
    if not testo_esistente or len(testo_esistente) < 50:
        # Prendi i primi 2000 caratteri come descrizione
        result["testo_nlp"] = html_text[:2000]

    return result
