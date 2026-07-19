#!/usr/bin/env python3
"""Contatta — esporta candidati da contattare per un bando.

Legge da radar-completo.json (già calcolato), arricchisce con contatti
da unified_ets + Google Places (opzionale), e produce CSV pronto per azione.

Uso:
    python3 match/reports/contatta.py --bando "BPER" --top 10
    python3 match/reports/contatta.py --bando "BPER" --top 10 --enrich
    python3 match/reports/contatta.py --cf 90081250632     # cerca bandi per ETS
    python3 match/reports/contatta.py --bando "BPER" --formato json
"""

import csv, json, sys
from datetime import datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))

from lib.format import fmt_euro

RADAR_JSON = ROOT / "cruscotto" / "radar-completo.json"
ETS_FILE = ROOT / "data" / "unified_ets.parquet"
OUTPUT_DIR = ROOT / "cruscotto"


# ── Google Places enrichment (opzionale) ─────────────────────────────

from lib.places import cerca_ets as cerca_google_places


# ── Contatti da unified_ets (sempre disponibili) ─────────────────────

_ETS_CACHE: dict | None = None

def _carica_ets_cache():
    """Carica unified_ets una tantum in memoria (dict CF → info)."""
    global _ETS_CACHE
    if _ETS_CACHE is not None:
        return _ETS_CACHE
    con = duckdb.connect()
    df = con.sql(f"""
        SELECT codice_fiscale, denominazione, comune, provincia, sezione,
               capacita_progettuale, importo_5x1000_2025,
               ha_finanziamenti_ue, ha_progetti_pnrr,
               appalti_riservati, appalti_pnrr
        FROM '{ETS_FILE.as_posix()}'
    """).fetchdf()
    con.close()
    import math
    _ETS_CACHE = {}
    for _, row in df.iterrows():
        cf = row.get("codice_fiscale", "")
        _ETS_CACHE[cf] = {
            "denominazione": str(row.get("denominazione", "") or ""),
            "comune": str(row.get("comune", "") or ""),
            "provincia": str(row.get("provincia", "") or ""),
            "sezione": str(row.get("sezione", "") or ""),
            "capacita": str(row.get("capacita_progettuale", "") or ""),
            "appalti_riservati": int(row.get("appalti_riservati", 0) or 0),
            "appalti_pnrr": int(row.get("appalti_pnrr", 0) or 0),
            "email": "", "sito": "", "telefono": "",
        }
    return _ETS_CACHE


def contatti_da_unified(cf):
    """Recupera contatti da unified_ets per un CF (da cache in memoria)."""
    cache = _carica_ets_cache()
    return cache.get(cf, {})


# ── Logica principale ────────────────────────────────────────────────

def carica_radar():
    if not RADAR_JSON.exists():
        print(f"❌ {RADAR_JSON} non trovato. Esegui prima 'make scan'.")
        sys.exit(1)
    with open(RADAR_JSON) as f:
        return json.load(f)


def cerca_per_bando(scan, pattern, top_n=10):
    """Cerca bandi il cui titolo contiene pattern, restituisce candidati."""
    risultati = []
    for r in scan["resultados"]:
        if pattern.lower() in r["titolo"].lower():
            for c in r["candidati"][:top_n]:
                risultati.append({
                    "bando": r["titolo"],
                    "bando_url": r.get("url", ""),
                    "bando_ente": r.get("ente", ""),
                    "bando_scadenza": r.get("scadenza", ""),
                    "bando_gg": r.get("gg_rimasti", r.get("gg", 999)),
                    "bando_budget": r.get("budget", ""),
                    "bando_tags": ", ".join(r.get("tags", [])),
                    "ets_cf": c.get("cf", ""),
                    "ets_denominazione": c.get("denominazione", ""),
                    "ets_capacita": c.get("capacita", c.get("capacita_progettuale", "")),
                    "ets_score": c.get("score", 0),
                    "ets_motivo": c.get("motivo", ""),
                })
    return risultati


def cerca_per_cf(scan, cf):
    """Cerca un ETS per CF, restituisce tutti i bandi dove è candidato."""
    risultati = []
    for r in scan["resultados"]:
        for c in r["candidati"]:
            if c.get("cf", "") == cf:
                risultati.append({
                    "bando": r["titolo"],
                    "bando_url": r.get("url", ""),
                    "bando_ente": r.get("ente", ""),
                    "bando_scadenza": r.get("scadenza", ""),
                    "bando_gg": r.get("gg_rimasti", r.get("gg", 999)),
                    "bando_budget": r.get("budget", ""),
                    "bando_tags": ", ".join(r.get("tags", [])),
                    "ets_cf": c.get("cf", ""),
                    "ets_denominazione": c.get("denominazione", ""),
                    "ets_capacita": c.get("capacita", c.get("capacita_progettuale", "")),
                    "ets_score": c.get("score", 0),
                    "ets_motivo": c.get("motivo", ""),
                })
    return risultati


def arricchisci_contatti(candidati, use_enrich=False):
    """Aggiunge contatti a ogni candidato."""
    arricchiti = []
    for cand in candidati:
        cf = cand["ets_cf"]
        info = contatti_da_unified(cf)
        cand["ets_comune"] = info.get("comune", cand.get("comune", ""))
        cand["ets_provincia"] = info.get("provincia", cand.get("provincia", ""))
        cand["ets_appalti_riservati"] = info.get("appalti_riservati", 0)
        cand["ets_appalti_pnrr"] = info.get("appalti_pnrr", 0)
        cand["ets_email"] = info.get("email", "")
        cand["ets_sito"] = info.get("sito", "")
        cand["ets_telefono"] = info.get("telefono", "")

        # Enrich opzionale con Google Places (per telefono/sito mancanti)
        if use_enrich and not (cand["ets_email"] or cand["ets_sito"] or cand["ets_telefono"]):
            gp = cerca_google_places(
                cand["ets_denominazione"],
                info.get("comune", ""),
            )
            if gp:
                cand["ets_telefono"] = cand["ets_telefono"] or gp.get("telefono", "")
                cand["ets_sito"] = cand["ets_sito"] or gp.get("sito_web", "")
                cand["ets_google_rating"] = gp.get("rating", "")
                cand["ets_google_recensioni"] = gp.get("totale_recensioni", "")

        # Flag contattabilità
        ha_contatti = bool(cand["ets_email"] or cand["ets_telefono"] or cand["ets_sito"])
        cand["ets_contattabile"] = "SI" if ha_contatti else "NO"

        # Messaggio personalizzato per chi telefona
        bando_nome = cand.get("bando", "")
        budget = cand.get("bando_budget", "")
        motivo = cand.get("ets_motivo", "")
        budget_txt = f" con budget {fmt_euro(budget)}" if budget else ""
        cand["ets_messaggio"] = (
            f"Buongiorno, sono {cand.get('ets_denominazione', '...')[:40]}? "
            f"La contatto per il bando '{bando_nome[:60]}'{budget_txt}. "
            f"Il nostro sistema la segnala come candidato ideale ({motivo[:80]}). "
            f"Ha 5 minuti per parlarne?"
        )

        arricchiti.append(cand)
    return arricchiti


def esporta_csv(candidati, output):
    """Scrive CSV."""
    if not candidati:
        print("❌ Nessun candidato da esportare")
        return

    fieldnames = list(candidati[0].keys())
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(candidati)
    print(f"✅ {len(candidati)} candidati esportati in {output}")


def esporta_json(candidati, output):
    """Scrive JSON."""
    with open(output, "w", encoding="utf-8") as f:
        json.dump(candidati, f, ensure_ascii=False, indent=2)
    print(f"✅ {len(candidati)} candidati esportati in {output}")


# ── ETS → Bandi (vista per ETS) ──────────────────────────────────────

def esporta_per_ets(scan, top_bandi=5):
    """Inverte: per ogni ETS, lista i suoi migliori bandi."""
    ets_bandi = {}
    for r in scan["resultados"]:
        for c in r["candidati"]:
            cf = c.get("cf", "")
            if not cf:
                continue
            ets_bandi.setdefault(cf, []).append({
                "bando": r["titolo"],
                "bando_url": r.get("url", ""),
                "bando_ente": r.get("ente", ""),
                "bando_scadenza": r.get("scadenza", ""),
                "bando_gg": r.get("gg_rimasti", r.get("gg", 999)),
                "bando_budget": r.get("budget", ""),
                "bando_tags": ", ".join(r.get("tags", [])),
                "ets_score": c.get("score", 0),
                "ets_motivo": c.get("motivo", ""),
            })

    risultati = []
    for cf, bandi in ets_bandi.items():
        info = contatti_da_unified(cf)
        for b in sorted(bandi, key=lambda x: -x["ets_score"])[:top_bandi]:
            risultati.append({
                "ets_cf": cf,
                "ets_denominazione": info.get("denominazione", ""),
                "ets_comune": info.get("comune", ""),
                "ets_provincia": info.get("provincia", ""),
                "ets_capacita": info.get("capacita", ""),
                "ets_appalti_riservati": info.get("appalti_riservati", 0),
                "ets_appalti_pnrr": info.get("appalti_pnrr", 0),
                "ets_email": "",
                "ets_sito": "",
                "ets_telefono": "",
                **b,
            })
    return risultati


def stampa_riepilogo(candidati, per_ets=False):
    """Stampa un riepilogo leggibile."""
    if not candidati:
        return

    if per_ets:
        # Raggruppa per CF
        from collections import OrderedDict
        gruppi = OrderedDict()
        for c in candidati:
            gruppi.setdefault(c["ets_cf"], []).append(c)

        for cf, bandi in gruppi.items():
            denom = bandi[0].get("ets_denominazione", cf)[:45]
            cap = bandi[0].get("ets_capacita", "?")
            print(f"\n📌 {denom}")
            print(f"   CF: {cf} | Capacità: {cap}")
            for b in bandi:
                urg = "🔴" if b["bando_gg"] <= 30 else "🟡" if b["bando_gg"] <= 60 else "  "
                print(f"   {urg} {b['bando'][:55]} — score {b['ets_score']}, scad. {b['bando_scadenza']} ({b['bando_gg']}gg)")
            cont = sum(1 for b in bandi if b.get("ets_telefono") or b.get("ets_email") or b.get("ets_sito"))
            print(f"   ⚡ {cont}/{len(bandi)} bandi con contatti")
        return

    # Default: raggruppa per bando
    from collections import OrderedDict
    bandi = OrderedDict()
    for c in candidati:
        bandi.setdefault(c["bando"], []).append(c)

    for bando, cands in bandi.items():
        scad = cands[0].get("bando_scadenza", "?")
        gg = cands[0].get("bando_gg", "?")
        ente = cands[0].get("bando_ente", "?")
        budget = cands[0].get("bando_budget", "")
        print(f"\n📌 {bando}")
        print(f"   Ente: {ente} | Scadenza: {scad} ({gg}gg) | Budget: {fmt_euro(budget) if budget else 'N/D'}")
        print(f"   {'CF':16s} {'ETS':45s} {'Cap':10s} {'Score':>5s} {'Contattabile':>12s}")
        print(f"   {'--':16s} {'---':45s} {'---':10s} {'----':>5s} {'-----------':>12s}")
        for c in cands:
            cf = c["ets_cf"][:16] if c["ets_cf"] else "?"
            denom = c["ets_denominazione"][:45]
            cap = c["ets_capacita"][:10]
            score = c["ets_score"]
            cont = c.get("ets_contattabile", "?")
            print(f"   {cf:16s} {denom:45s} {cap:10s} {score:5d} {cont:>12s}")
        contattabili = sum(1 for c in cands if c.get("ets_contattabile") == "SI")
        print(f"   ⚡ {contattabili}/{len(cands)} contattabili")
        if contattabili == 0 and not any(c.get("ets_google_rating") for c in cands):
            print(f"   💡 Nessun contatto trovato. Riprova con --enrich per cercare su Google Places.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Esporta candidati da contattare")
    parser.add_argument("--bando", help="Filtra bandi per testo nel titolo")
    parser.add_argument("--cf", help="Cerca bandi per CF ETS")
    parser.add_argument("--per-ets", action="store_true", help="Inverte: per ogni ETS, i suoi migliori bandi")
    parser.add_argument("--top", type=int, default=10, help="Top N candidati per bando o top N bandi per ETS (default: 10)")
    parser.add_argument("--enrich", action="store_true", help="Arricchisci con Google Places (lento, serve API key)")
    parser.add_argument("--formato", choices=["csv", "json"], default="csv", help="Formato output")
    parser.add_argument("--output", help="File output (default: contatta-{modalità}-{data}.{csv|json})")
    args = parser.parse_args()

    scan = carica_radar()

    # Modalità: per ETS (inverte il flusso)
    if args.per_ets:
        slug = "per-ets"
        candidati = esporta_per_ets(scan, top_bandi=args.top)
        print(f"📋 {len(candidati)} righe: {len(set(c['ets_cf'] for c in candidati))} ETS × top {args.top} bandi")
        candidati = arricchisci_contatti(candidati, use_enrich=args.enrich)
        oggi = datetime.now().strftime("%Y%m%d")
        output = args.output or str(OUTPUT_DIR / f"contatta-{slug}-{oggi}.{args.formato}")
        if args.formato == "csv":
            esporta_csv(candidati, output)
        else:
            esporta_json(candidati, output)
        stampa_riepilogo(candidati, per_ets=True)
        return

    # Modalità: per bando o per CF singolo
    if not args.bando and not args.cf:
        parser.print_help()
        print("\n❌ Specifica --bando, --cf o --per-ets")
        sys.exit(1)

    if args.bando:
        candidati = cerca_per_bando(scan, args.bando, top_n=args.top)
        if not candidati:
            print(f"❌ Nessun bando trovato per: '{args.bando}'")
            suggeriti = [r["titolo"] for r in scan["resultados"] if args.bando.lower() in r["titolo"].lower()]
            if suggeriti:
                print(f"   Suggerimento: {' | '.join(suggeriti[:5])}")
            sys.exit(1)
        slug = args.bando.lower().replace(" ", "-")[:30]
    elif args.cf:
        candidati = cerca_per_cf(scan, args.cf)
        if not candidati:
            print(f"❌ ETS con CF '{args.cf}' non trovato tra i candidati")
            sys.exit(1)
        slug = f"ets-{args.cf[:8]}"

    print(f"🔍 Arricchisco {len(candidati)} candidati con contatti...")
    candidati = arricchisci_contatti(candidati, use_enrich=args.enrich)

    oggi = datetime.now().strftime("%Y%m%d")
    output = args.output or str(OUTPUT_DIR / f"contatta-{slug}-{oggi}.{args.formato}")

    if args.formato == "csv":
        esporta_csv(candidati, output)
    else:
        esporta_json(candidati, output)

    stampa_riepilogo(candidati)


if __name__ == "__main__":
    main()
