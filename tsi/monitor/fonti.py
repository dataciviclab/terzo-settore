"""Healthcheck su tutte le fonti registrate.

Uso:
    python3 -m tsi.monitor.fonti
"""

from tsi.bandi.registry import Registry
from tsi.bandi.fonti.infobandi import InfobandiAdapter
from tsi.bandi.fonti.info_coop import InfoCoopAdapter


def report_fonti() -> list[dict]:
    """Esegue healthcheck su tutte le fonti e produce report."""
    registry = Registry()
    registry.carica("infobandi", InfobandiAdapter)
    registry.carica("info-cooperazione", InfoCoopAdapter)
    return registry.healthcheck()


def stampa_report():
    """Stampa report leggibile."""
    risultati = report_fonti()
    print(f"{'Fonte':25s} {'Stato':10s} {'TTL':8s} {'Status':15s}")
    print(f"{'':-25s} {'':-10s} {'':-8s} {'':-15s}")
    for r in risultati:
        icona = "✅" if r["stato"] == "ok" else "❌"
        print(f"{icona} {r['nome']:22s} {r['stato']:10s} {r['ttl']:>6d}s {r['status']:15s}")


if __name__ == "__main__":
    stampa_report()
