"""Registry delle fonti di bandi.

Ogni fonte è un adapter registrato con nome, TTL e stato.
Le fonti si aggiungono con una riga di config.
"""

from __future__ import annotations
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from tsi.bandi.base import FonteBandi, BandoNormalizzato

logger = logging.getLogger(__name__)


class Registry:
    """Catalogo delle fonti di bandi disponibili.

    Uso:
        registry = Registry()
        registry.carica("infobandi", InfobandiAdapter, ttl=3600)

        # Fetch da tutte le fonti attive
        bandi = registry.fetch_tutti()
        # Fetch da una fonte specifica
        bandi_infobandi = registry.fetch("infobandi")
    """

    def __init__(self):
        self._fonti: dict[str, dict] = {}

    def carica(
        self,
        nome: str,
        adapter_cls: type[FonteBandi],
        ttl: int | None = None,
        stato: str = "attivo",
    ) -> None:
        """Registra una fonte nel catalogo.

        Args:
            nome: identificativo unico (es. \"infobandi\")
            adapter_cls: classe adapter che implementa FonteBandi
            ttl: secondi tra refresh (default: dalla classe)
            stato: \"attivo\" | \"candidate\" | \"disabilitato\"
        """
        if nome in self._fonti:
            logger.warning(f"Fonte '{nome}' già registrata, sovrascrivo")
        self._fonti[nome] = {
            "adapter_cls": adapter_cls,
            "adapter": None,
            "ttl": ttl or adapter_cls.ttl_secondi,
            "stato": stato,
            "ultimo_ok": None,
            "ultimo_errore": None,
        }

    def lista(self, solo_attive: bool = True) -> dict[str, dict]:
        """Elenco fonti con stato e metadata."""
        if solo_attive:
            return {n: c for n, c in self._fonti.items() if c["stato"] == "attivo"}
        return dict(self._fonti)

    def healthcheck(self) -> list[dict]:
        """Healthcheck su tutte le fonti registrate."""
        risultati = []
        for nome, cfg in self._fonti.items():
            adapter = self._get_adapter(nome, cfg)
            ok = adapter.health()
            risultati.append({
                "nome": nome,
                "stato": "ok" if ok else "errore",
                "ttl": cfg["ttl"],
                "status": cfg["stato"],
            })
            if ok:
                cfg["ultimo_ok"] = True
            else:
                cfg["ultimo_errore"] = True
        return risultati

    def fetch(self, nome: str) -> list[BandoNormalizzato]:
        """Fetch da una fonte specifica."""
        cfg = self._fonti.get(nome)
        if not cfg:
            logger.error(f"Fonte '{nome}' non trovata nel registry")
            return []
        if cfg["stato"] != "attivo":
            logger.info(f"Fonte '{nome}' in stato '{cfg['stato']}', salto")
            return []
        adapter = self._get_adapter(nome, cfg)
        if not adapter.health():
            logger.warning(f"Fonte '{nome}' non raggiungibile")
            cfg["ultimo_errore"] = True
            return []
        try:
            bandi = adapter.fetch()
            cfg["ultimo_ok"] = True
            return bandi
        except Exception as e:
            logger.error(f"Fonte '{nome}': fetch fallito: {e}")
            cfg["ultimo_errore"] = str(e)
            return []

    def fetch_tutti(self) -> list[BandoNormalizzato]:
        """Fetch da tutte le fonti attive."""
        tutti = []
        for nome in self._fonti:
            if self._fonti[nome]["stato"] == "attivo":
                bandi = self.fetch(nome)
                tutti.extend(bandi)
        return tutti

    def _get_adapter(self, nome: str, cfg: dict) -> FonteBandi:
        if cfg["adapter"] is None:
            cfg["adapter"] = cfg["adapter_cls"]()
        return cfg["adapter"]
