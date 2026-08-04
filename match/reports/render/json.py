"""Render JSON: vista analytics → dict JSON-serializzabile.

Le viste analytics sono già dict puri; qui aggiungiamo il contesto
(metadata) e normalizziamo i tipi per la serializzazione.
"""

from datetime import datetime


def _clean(obj):
    """Rende un oggetto JSON-serializzabile (gestisce tipi numpy/date)."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    try:
        import pandas as pd
        if pd.isna(obj):
            return None
    except (TypeError, ValueError):
        pass
    return str(obj)


def segnale(vista):
    return _clean(vista)


def latest(vista):
    return _clean(vista)


def completo(scan):
    """Radar completo: stessa struttura del JSON pre-refactor (backward-compat)."""
    from lib.format import fmt_match_reason

    return {
        "generato": datetime.now().isoformat(),
        "bandi_totali": len(scan["bandi"]),
        "match": len(scan["resultados"]),
        "gap": len(scan["sin_match"]),
        "esclusi": len(scan["skipped"]),
        "ets_unici": len(scan["stats_ets"]),
        "resultados": [
            {"titolo": r["titolo"], "url": r["url"], "ente": r["ente"], "budget": r.get("budget"),
             "scadenza": r["scadenza"], "gg_rimasti": r["gg"], "status": r["status"],
             "territorio": r["territorio"], "tags": r["tags"],
             "candidati": [{"cf": cand.get("codice_fiscale"), "denominazione": cand["denominazione"],
                            "comune": cand.get("comune"), "provincia": cand.get("provincia"),
                            "capacita": cand["capacita_progettuale"], "sezione": cand.get("sezione"),
                            "score": int(cand.get("score", 0)), "motivo": fmt_match_reason(cand),
                            "importo_5x1000_2025": cand.get("importo_5x1000_2025")} for cand in r["candidati"]]}
            for r in scan["resultados"]
        ],
        "sin_match": [{"titolo": t[0], "url": t[1], "ente": t[2], "scadenza": t[3],
                       "gg_rimasti": t[4], "tags": t[5], "territorio": t[6], "status": t[7], "motivo": t[8]}
                      for t in scan["sin_match"]],
        "esclusi": [{"titolo": s["titolo"], "status": s["status"], "motivo": s["motivo"]} for s in scan["skipped"]],
    }
