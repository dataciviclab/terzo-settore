#!/usr/bin/env python3
"""Scheda ETS: profilo completo di un ente del Terzo Settore.

Uso:
    python3 radar/scheda.py --cf 02006180364          # per CF
    python3 radar/scheda.py --nome "nazareno"          # per nome
    python3 radar/scheda.py --cf 02006180364 --anac    # con dettaglio ANAC
    python3 radar/scheda.py --cf 02006180364 --match   # con bandi matchati
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

import duckdb
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))

from radar.core import fmt_euro, fmt_match_reason, is_missing

GCS = "https://storage.googleapis.com/dataciviclab-clean"
ETS_FILE = str(ROOT / "data/unified_ets.parquet")


def cerca_ets(cf=None, nome=None):
    """Cerca ETS per CF o nome."""
    con = duckdb.connect()
    if cf:
        r = con.sql(f"SELECT * FROM '{ETS_FILE}' WHERE codice_fiscale = '{cf}'").fetchdf()
    elif nome:
        r = con.sql(f"""
            SELECT * FROM '{ETS_FILE}' 
            WHERE lower(denominazione) LIKE '%{nome.lower()}%'
            ORDER BY importo_appalti DESC
            LIMIT 10
        """).fetchdf()
    else:
        print("❌ Specifica --cf o --nome")
        return None
    con.close()
    if r.empty:
        print("❌ Nessun ETS trovato")
        return None
    return r


def scheda_base(row):
    """Stampa scheda base ETS."""
    print(f"\n{'='*60}")
    print(f"📋 SCHEDA ETS")
    print(f"{'='*60}")
    print(f"   Denominazione:    {row['denominazione']}")
    print(f"   Codice Fiscale:   {row['codice_fiscale']}")
    print(f"   Sezione RUNTS:    {row['sezione']}")
    print(f"   Sede:             {row['comune']} ({row['provincia']})")
    print(f"   Data iscrizione:  {row.get('data_iscrizione', '?')}")
    print()
    print(f"   Capacità:         {row['capacita_progettuale']}")
    print(f"   5x1000 2025:      {fmt_euro(row.get('cinque_2025'))}")
    print(f"   5x1000 totale:    {fmt_euro(row.get('cinque_totale'))}")
    print(f"   5x1000 anni:      {int(row['cinque_anni']) if not is_missing(row.get('cinque_anni')) else 0}")
    print(f"   Grant UE:         {'✅' if row.get('ha_grant_ue') else '❌'} {fmt_euro(row.get('grant_ue_totale'))}")
    print(f"   Aiuti Stato:      {'✅' if row.get('ha_aiuti_stato') else '❌'} {fmt_euro(row.get('aiuti_stato_totale'))}")
    print(f"   PNRR:             {'✅' if row.get('ha_pnrr') else '❌'} {fmt_euro(row.get('pnrr_totale'))}")
    print(f"   Appalti ANAC:     {'✅' if row.get('ha_appalti') else '❌'} {fmt_euro(row.get('importo_appalti'))}")
    print(f"   Temi ANAC:        {row.get('temi_anac', '') or 'nessuno'}")
    return row['codice_fiscale']


def scheda_anac(cf, con):
    """Dettaglio ANAC: aggiudicazioni e partecipazioni."""
    print(f"\n{'─'*60}")
    print(f"📊 DETTAGLIO ANAC")
    print(f"{'─'*60}")

    # Aggiudicazioni 2026
    r = con.sql(f"""
        SELECT COUNT(DISTINCT a.cig) as n_gare,
               ROUND(SUM(ag.importo_aggiudicazione), 0) as importo_tot,
               ROUND(AVG(ag.importo_aggiudicazione), 0) as importo_medio,
               ROUND(MAX(ag.importo_aggiudicazione), 0) as importo_max,
               ROUND(MIN(ag.importo_aggiudicazione), 0) as importo_min
        FROM read_parquet('{GCS}/anac_aggiudicatari/2026/anac_aggiudicatari_2026_clean.parquet', union_by_name=true) a
        INNER JOIN read_parquet('{GCS}/anac_aggiudicazioni/2026/anac_aggiudicazioni_2026_clean.parquet', union_by_name=true) ag
            ON a.cig = ag.cig
        WHERE a.codice_fiscale = '{cf}'
          AND ag.importo_aggiudicazione > 0
    """).fetchdf()
    if not r.empty and r['n_gare'].iloc[0] > 0:
        print(f"\n   Aggiudicazioni 2026:")
        print(f"      Numero gare:      {int(r['n_gare'].iloc[0])}")
        print(f"      Importo totale:   €{float(r['importo_tot'].iloc[0]):,.0f}")
        print(f"      Media a gara:     €{float(r['importo_medio'].iloc[0]):,.0f}")
        print(f"      Max gara:         €{float(r['importo_max'].iloc[0]):,.0f}")
        print(f"      Min gara:         €{float(r['importo_min'].iloc[0]):,.0f}")
    else:
        print(f"\n   Aggiudicazioni 2026: ❌ nessuna")

    # Partecipazioni 2026
    r2 = con.sql(f"""
        SELECT COUNT(DISTINCT cig) as n_partecipazioni
        FROM read_parquet('{GCS}/anac_partecipanti/2026/anac_partecipanti_2026_clean.parquet', union_by_name=true)
        WHERE codice_fiscale = '{cf}'
    """).fetchdf()
    n_part = int(r2['n_partecipazioni'].iloc[0]) if not r2.empty else 0
    print(f"   Partecipazioni 2026: {'✅' if n_part > 0 else '❌'} {n_part}")

    # Fatturato reale (da reportaziende)
    print(f"\n   📌 Fatturato reale (da camera di commercio):")
    try:
        url = f"https://www.reportaziende.it/{cf[:8]}_{cf[8:]}_mo_{cf}"
        # Non funziona direttamente, proviamo con una search
        resp = requests.get(
            f"https://www.reportaziende.it/search?q={cf}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        if resp.status_code == 200 and "Fatturato" in resp.text:
            for m in re.finditer(r'Fatturato\s+\d{4}[:\s]+[€\s]*([\d.]+)', resp.text):
                print(f"      {m.group(0)[:60]}")
        else:
            print(f"      (dati non disponibili, servizio a pagamento)")
    except Exception:
        print(f"      (errore nella ricerca)")


def scheda_match(cf, con):
    """Bandi matchati per questo ETS."""
    print(f"\n{'─'*60}")
    print(f"🎯 BANDI MATCHATI")
    print(f"{'─'*60}")

    radar_json = ROOT / "cruscotto" / "radar-completo.json"
    if not radar_json.exists():
        print(f"   ❌ radar-completo.json non trovato. Esegui make scan")
        return

    with open(radar_json) as f:
        scan = json.load(f)

    trovati = []
    for r in scan["resultados"]:
        for c in r.get("candidati", []):
            if c.get("cf", "") == cf:
                trovati.append({
                    "bando": r["titolo"],
                    "budget": r.get("budget"),
                    "scadenza": r.get("scadenza", ""),
                    "gg": r.get("gg_rimasti", r.get("gg", 999)),
                    "score": c.get("score", 0),
                    "motivo": c.get("motivo", ""),
                })
                break

    if not trovati:
        print(f"   ❌ Non presente nei match di nessun bando")
        return

    trovati.sort(key=lambda x: -x["score"])
    print(f"   Trovato in {len(trovati)} bandi:")
    print(f"   {'Score':>5s} {'GG':>4s} {'Bando'}")
    print(f"   {'─'*5} {'─'*4} {'─'*40}")
    for t in trovati[:10]:
        urg = "🔴" if t["gg"] <= 30 else ("🟡" if t["gg"] <= 60 else "  ")
        print(f"   {t['score']:>5d} {urg}{t['gg']:>3d} {t['bando'][:50]}")
        print(f"   {t['motivo'][:80]}")
        print()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Scheda ETS")
    parser.add_argument("--cf", help="Codice Fiscale ETS")
    parser.add_argument("--nome", help="Nome ETS (ricerca LIKE)")
    parser.add_argument("--anac", action="store_true", help="Mostra dettaglio ANAC")
    parser.add_argument("--match", action="store_true", help="Mostra bandi matchati")
    args = parser.parse_args()

    if not args.cf and not args.nome:
        parser.print_help()
        print("\n❌ Specifica --cf o --nome")
        sys.exit(1)

    rows = cerca_ets(cf=args.cf, nome=args.nome)
    if rows is None:
        sys.exit(1)

    con = duckdb.connect()

    for idx, (_, row) in enumerate(rows.iterrows()):
        if len(rows) > 1:
            print(f"\n{'#'*60}")
            print(f"# RISULTATO {idx+1}/{len(rows)}")
            print(f"{'#'*60}")
        cf = scheda_base(row)
        if args.anac:
            scheda_anac(cf, con)
        if args.match:
            scheda_match(cf, con)

    con.close()


if __name__ == "__main__":
    main()
