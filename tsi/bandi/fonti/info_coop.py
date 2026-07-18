"""Adapter per Info-cooperazione.

Fonte: https://www.info-cooperazione.it/bandi/
Affidabilità: bassa (HTML scraping puro, struttura può cambiare)
"""

from datetime import date, datetime
import logging
import re
import time
from typing import ClassVar

import requests
from bs4 import BeautifulSoup

from tsi.bandi.base import BandoNormalizzato, FonteBandi

logger = logging.getLogger(__name__)

BASE_URL = "https://www.info-cooperazione.it"
BANDI_URL = f"{BASE_URL}/bandi/"
HEADERS = {"User-Agent": "tsi/0.2 (+https://github.com/dataciviclab/terzo-settore-intelligence)"}

MESI_IT = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4,
    "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
    "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}


class InfoCoopAdapter(FonteBandi):
    """Adapter per info-cooperazione.it."""

    nome: ClassVar[str] = "info-cooperazione"
    ttl_secondi: ClassVar[int] = 7200

    def health(self) -> bool:
        """Verifica che la pagina bandi sia raggiungibile e contenga elementi attesi."""
        try:
            resp = requests.get(BANDI_URL, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                return False
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select("article, .bando-card, .post-card, .bandi-item")
            return len(cards) > 0
        except requests.RequestException:
            return False

    def fetch(self) -> list[BandoNormalizzato]:
        try:
            return self._fetch_tutti()
        except Exception as e:
            logger.error(f"Info-cooperazione fetch fallito: {e}")
            return []

    def _fetch_tutti(self, max_pagine: int = 10) -> list[BandoNormalizzato]:
        """Scorre le pagine del listato bandi e recupera i dettagli."""
        risultati = []
        visti_url = set()

        for pagina in range(1, max_pagine + 1):
            url = f"{BANDI_URL}page/{pagina}/" if pagina > 1 else BANDI_URL
            try:
                resp = requests.get(url, headers=HEADERS, timeout=20)
                if resp.status_code != 200:
                    break
                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.select("article, .bando-card, .post-card")
                if not cards:
                    break
                for card in cards:
                    b = self._da_card(card)
                    if b and b.url not in visti_url:
                        visti_url.add(b.url)
                        risultati.append(b)
            except requests.RequestException:
                break
            time.sleep(0.5)

        return risultati

    def _da_card(self, card) -> BandoNormalizzato | None:
        """Estrae un bando da un elemento card della lista."""
        link = card.find("a")
        if not link or not link.get("href"):
            return None
        url = link["href"] if link["href"].startswith("http") else BASE_URL + link["href"]
        titolo = link.get_text(strip=True) or "?"
        return BandoNormalizzato(
            titolo=titolo,
            ente="?",  # ente nel dettaglio
            scadenza=None,
            budget=None,
            url=url,
            territorio="Nazionale/da verificare",
            tags=[],
            descrizione="",
            fonte=self.nome,
            id_fonte=url.split("/")[-2] if url.endswith("/") else url.split("/")[-1],
        )
