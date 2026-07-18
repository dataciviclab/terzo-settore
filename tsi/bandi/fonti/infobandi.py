"""Adapter per Infobandi (CSVNet).

Fonte: https://infobandi.csvnet.it/ (API WordPress + RSS)
Affidabilità: media (API stabile, HTML scraping per campi strutturati)
"""

from datetime import date, datetime
import logging
import re
from typing import ClassVar

import requests

from tsi.bandi.base import BandoNormalizzato, FonteBandi

logger = logging.getLogger(__name__)

API_BASE = "https://infobandi.csvnet.it/wp-json/wp/v2"
HEADERS = {"User-Agent": "tsi/0.2 (+https://github.com/dataciviclab/terzo-settore-intelligence)"}


class InfobandiAdapter(FonteBandi):
    """Adapter per infobandi.csvnet.it."""

    nome: ClassVar[str] = "infobandi"
    ttl_secondi: ClassVar[int] = 3600

    def health(self) -> bool:
        """Verifica che l'API WordPress sia raggiungibile."""
        try:
            resp = requests.get(
                f"{API_BASE}/posts?per_page=1&_fields=id",
                headers=HEADERS, timeout=10,
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def fetch(self) -> list[BandoNormalizzato]:
        try:
            return self._fetch_bandi()
        except Exception as e:
            logger.error(f"Infobandi fetch fallito: {e}")
            return []

    def _fetch_bandi(self) -> list[BandoNormalizzato]:
        """Recupera tutti i post dall'API WordPress."""
        bandi = []
        page = 1
        while True:
            url = f"{API_BASE}/posts?per_page=100&page={page}&_fields=id,date,title,link,categories,tags,content"
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            for post in data:
                b = self._normalizza(post)
                if b.valido:
                    bandi.append(b)
            total = int(resp.headers.get("X-WP-Total", 0))
            if len(bandi) >= total:
                break
            page += 1
        return bandi

    def _normalizza(self, post: dict) -> BandoNormalizzato:
        """Converte un post WordPress in BandoNormalizzato."""
        html = post.get("content", {}).get("rendered", "")
        testo = re.sub(r"<[^>]+>", " ", html)
        testo = re.sub(r"\s+", " ", testo).strip()

        titolo = post["title"]["rendered"]
        ente = self._campo(html, "ENTE EROGATORE") or "?"
        scadenza_str = self._campo(html, "SCADENZA")
        scadenza = self._parse_scadenza(scadenza_str) if scadenza_str else None
        budget = self._parse_budget(testo)
        tags_raw = re.findall(r'rel="tag">([^<]+)<', html)

        return BandoNormalizzato(
            titolo=titolo,
            ente=ente,
            scadenza=scadenza,
            budget=budget,
            url=post["link"],
            territorio="Nazionale/da verificare",
            tags=tags_raw,
            descrizione=testo[:2000],
            fonte=self.nome,
            id_fonte=str(post["id"]),
            scaduto=self._e_scaduto(scadenza) if scadenza else False,
        )

    # ── helper ─────────────────────────────────────────────

    MESI_IT = {
        "gennaio": "01", "febbraio": "02", "marzo": "03", "aprile": "04",
        "maggio": "05", "giugno": "06", "luglio": "07", "agosto": "08",
        "settembre": "09", "ottobre": "10", "novembre": "11", "dicembre": "12",
    }

    @staticmethod
    def _campo(html: str, label: str) -> str | None:
        pattern = re.compile(
            rf"{label}\s*</strong></p>\s*<p[^>]*>(.*?)(?:</p>|<(?:ul|h|p\s))", re.DOTALL
        )
        m = pattern.search(html)
        if m:
            return re.sub(r"<[^>]+>", "", m.group(1)).strip()[:500]
        return None

    @classmethod
    def _parse_scadenza(cls, raw: str) -> date | None:
        s = re.sub(r"\s+alle\s+ore\s+[\d:.]+", "", raw)
        s = re.sub(r"\s*\([^)]*\)\s*", " ", s)
        s = re.sub(r"\s+ore\s+[\d:.]+", "", s)
        s = s.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        m = re.match(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})", s, re.IGNORECASE)
        if m:
            giorno, mese, anno = m.group(1), m.group(2).lower(), m.group(3)
            if mese in cls.MESI_IT:
                try:
                    return date(int(anno), int(cls.MESI_IT[mese]), int(giorno))
                except ValueError:
                    return None
        return None

    @staticmethod
    def _parse_budget(testo: str) -> float | None:
        # Pattern 1: importo con punti separatori: 50.000, 1.944.818
        pattern = re.compile(
            r"(?:budget|stanziamento|dotazione|importo|finanziamento|risorse|plafond|contributo|totale|ammontare)"
            r"(?:\s+(?:complessiv[ao]|totale|massimo|previsto|stanziato|iniziale|disponibile|finale|richiesto)){0,2}"
            r".{0,80}?"
            r"(?:di|pari a|è di|fino a|massimo|€)?"
            r"\s*([1-9]\d{0,2}(?:[.\s]\d{3})+)"
            r"(?:\s*(?:euro|€))?",
            re.IGNORECASE | re.DOTALL
        )
        m = pattern.search(testo)
        if m:
            raw = m.group(1).strip().replace(" ", "").replace(".", "")
            try:
                return float(raw)
            except ValueError:
                pass
        
        # Pattern 2: "X milioni di euro"
        m2 = re.search(
            r"(?:budget|stanziamento|dotazione|importo|finanziamento|risorse|plafond|contributo|totale|ammontare)"
            r".{0,80}?"
            r"(?:di|è di|pari a)?"
            r"\s*([\d,]+)\s*(?:milioni?)\s*(?:di\s*)?(?:euro|€)",
            testo, re.IGNORECASE | re.DOTALL
        )
        if m2:
            raw = m2.group(1).strip().replace(",", ".")
            try:
                return float(raw) * 1_000_000
            except ValueError:
                pass
        return None

    @staticmethod
    def _e_scaduto(scadenza: date) -> bool:
        return scadenza < date.today()
