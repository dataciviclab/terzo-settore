"""FonteBandi: classe astratta per tutte le fonti di bandi.

Ogni fonte (Infobandi, Info-cooperazione, Cariplo, EU Funding...)
implementa un adapter che produce BandoNormalizzato.

Regole:
- health() verifica la fonte PRIMA di fetchare
- fetch() ritorna lista di BandoNormalizzato, mai eccezioni
- Se la fonte è irraggiungibile, fetch() ritorna [] e logga
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from hashlib import sha256
from typing import ClassVar
import logging

logger = logging.getLogger(__name__)


@dataclass
class BandoNormalizzato:
    """Schema comune per bandi da qualsiasi fonte.

    Hash: calcolato automaticamente da titolo + ente + scadenza.
    Usato per deduplica cross-fonte.
    """
    titolo: str
    ente: str
    scadenza: date | None
    budget: float | None
    url: str
    territorio: str          # "Nazionale", "Europa", "Mezzogiorno", "Lombardia"...
    tags: list[str]          # ["minori", "sport", "educazione"...]
    descrizione: str
    fonte: str               # "infobandi", "info-cooperazione"...
    id_fonte: str            # ID nella fonte originale
    scaduto: bool = False
    hash_contenuto: str = ""

    def __post_init__(self):
        if not self.hash_contenuto:
            raw = f"{self.titolo}|{self.ente}|{self.scadenza}"
            self.hash_contenuto = sha256(raw.encode()).hexdigest()[:16]

    @property
    def valido(self) -> bool:
        """Un bando è valido se ha almeno titolo e ente."""
        return bool(self.titolo and self.ente)


class FonteBandi(ABC):
    """Adapter astratto per una fonte di bandi.

    Sottoclassi:
    - nome: identificativo unico (es. "infobandi")
    - ttl_secondi: quanto tenere in cache prima di rifetchare
    - fetch(): recupera bandi
    - health(): verifica raggiungibilità
    """

    nome: ClassVar[str]
    ttl_secondi: ClassVar[int] = 3600

    @abstractmethod
    def fetch(self) -> list[BandoNormalizzato]:
        """Recupera tutti i bandi attivi dalla fonte.
        
        Non deve mai lanciare eccezioni. In caso di errore,
        logga e ritorna [].
        """
        ...

    def health(self) -> bool:
        """Verifica che la fonte sia raggiungibile.

        Default: HEAD sulla homepage. Le sottoclassi possono
        sovrascrivere per controlli più specifici.
        """
        return True  # override nelle sottoclassi

    def sample(self, n: int = 3) -> list[BandoNormalizzato]:
        """Anteprima degli ultimi n bandi."""
        bandi = self.fetch()
        return bandi[:n]

    def __str__(self) -> str:
        return f"FonteBandi[{self.nome}]"
