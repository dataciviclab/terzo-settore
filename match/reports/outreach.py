#!/usr/bin/env python3
"""Outreach — kit di scoperta per un territorio pilota.

Seleziona un campione bilanciato di ETS (per capacità e tipologia), genera
per ciascuno una scheda profilo leggibile (dati che già abbiamo + bandi
matchati), prepara il questionario di scoperta e la shortlist CSV con
contatti arricchiti via Google Places.

Obiettivo del pilota: andare a parlare con ETS reali e capire i loro bisogni
effettivi, usando i nostri dati come apertura di conversazione.

Uso:
    python3 match/reports/outreach.py BO
    python3 match/reports/outreach.py BO --n 10 --seed 42
    python3 match/reports/outreach.py BO --enrich       # Google Places (lento)
    python3 match/reports/outreach.py BO --csv-only     # solo shortlist
"""

import argparse, csv, json, random, sys
from datetime import datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))

from lib.format import fmt_euro

ETS_FILE = ROOT / "data" / "unified_ets.parquet"
RADAR_JSON = ROOT / "cruscotto" / "radar-completo.json"
OUTPUT_DIR = ROOT / "cruscotto" / "output"
REPORTING = ROOT / "data" / "reporting" / "outreach"

# Quota per livello di capacità: coprire tutto lo spettro, con peso maggiore
# sui livelli "medi" (i più numerosi e i più realistici da aiutare).
QUOTE_CAPACITA = {
    "alta": 2,
    "medio-alta": 2,
    "media": 2,
    "base": 2,
    "sconosciuta": 2,
}

# Livello di capacità preferito per ogni tipologia (per evitare campioni
# sbilanciati, es. sole APS piccole o sole imprese sociali forti).
SEZIONI_PREFERITE = [
    "IMPRESE SOCIALI",
    "ORGANIZZAZIONI DI VOLONTARIATO",
    "ASSOCIAZIONI DI PROMOZIONE SOCIALE",
    "ALTRI ENTI DEL TERZO SETTORE",
    "ENTI FILANTROPICI",
]


def carica_radar():
    if not RADAR_JSON.exists():
        return None
    with open(RADAR_JSON) as f:
        return json.load(f)


def ets_matchati_per_cf(scan, provincia):
    """CF degli ETS del territorio comparsi in almeno un bando, con i match."""
    by_cf = {}
    if not scan:
        return by_cf
    for r in scan.get("resultados", []):
        for c in r.get("candidati", []):
            if c.get("provincia") != provincia:
                continue
            by_cf.setdefault(c["cf"], []).append({
                "bando": r["titolo"],
                "ente": r.get("ente", ""),
                "budget": r.get("budget", ""),
                "scadenza": r.get("scadenza", ""),
                "gg": r.get("gg_rimasti", r.get("gg", 999)),
                "score": c.get("score", 0),
                "motivo": c.get("motivo", ""),
            })
    return by_cf


def campiona(con, provincia, n=10, seed=42):
    """Campionamento stratificato: quote per capacità, varianza di tipologia."""
    rng = random.Random(seed)
    scan = carica_radar()
    match_by_cf = ets_matchati_per_cf(scan, provincia)

    def pool(cap):
        """Pool di ETS per capacità, preferendo chi è già comparso nei bandi."""
        df = con.sql(f"""
            SELECT codice_fiscale, denominazione, comune, sezione, capacita_progettuale,
                   importo_5x1000_2025, numero_appalti
            FROM '{ETS_FILE}'
            WHERE provincia = '{provincia}'
              AND (capacita_progettuale = '{cap}' OR '{cap}' = 'sconosciuta' AND capacita_progettuale IS NULL)
            ORDER BY numero_appalti DESC NULLS LAST, importo_5x1000_2025 DESC NULLS LAST
        """).fetchdf()
        records = df.to_dict("records")
        if records:
            rng.shuffle(records)
            records.sort(key=lambda r: r["codice_fiscale"] in match_by_cf, reverse=True)
        return records

    # Assegna quota per capacità, poi bilancia la tipologia dentro ogni livello
    selezionati = []
    for cap, quota in QUOTE_CAPACITA.items():
        pool_cap = pool(cap)
        # round-robin sulle sezioni preferite, rimescolando tra giri
        picked = []
        it = 0
        while len(picked) < quota and pool_cap:
            start = it * len(SEZIONI_PREFERITE) % max(len(SEZIONI_PREFERITE), 1)
            round_cap = pool_cap[start:] + pool_cap[:start]
            found = next((e for e in round_cap if e["codice_fiscale"] not in [p["codice_fiscale"] for p in picked]), None)
            if not found:
                break
            picked.append(found)
            pool_cap = [e for e in pool_cap if e["codice_fiscale"] != found["codice_fiscale"]]
            it += 1
        selezionati.extend(picked)

    # Se non si raggiunge n, riempi con i restanti "media" non ancora presi
    while len(selezionati) < n:
        for cap in ("sconosciuta", "media", "base"):
            pool_cap = pool(cap)
            extra = next((e for e in pool_cap if e["codice_fiscale"] not in [p["codice_fiscale"] for p in selezionati]), None)
            if extra:
                selezionati.append(extra)
                break

    # Attacca i bandi matchati
    for e in selezionati:
        e["bandi_match"] = sorted(match_by_cf.get(e["codice_fiscale"], []), key=lambda b: -b["score"])
    return selezionati[:n]


def scheda_ets(con, row):
    """Profilo dati completo di un ETS (da unified_ets)."""
    cf = row["codice_fiscale"]
    df = con.sql(f"SELECT * FROM '{ETS_FILE}' WHERE codice_fiscale = '{cf}'").fetchdf()
    if df.empty:
        return None
    r = df.iloc[0]
    return {
        "codice_fiscale": cf,
        "denominazione": r.get("denominazione", ""),
        "sezione": r.get("sezione", ""),
        "comune": r.get("comune", ""),
        "provincia": r.get("provincia", ""),
        "data_iscrizione": str(r.get("data_iscrizione", ""))[:10],
        "capacita": r.get("capacita_progettuale", ""),
        "5x1000_2025": r.get("importo_5x1000_2025", 0),
        "5x1000_totale": r.get("importo_5x1000_totale", 0),
        "ue": r.get("ha_finanziamenti_ue", False),
        "importo_ue": r.get("importo_ue", 0),
        "aiuti_stato": r.get("ha_aiuti_stato", False),
        "importo_aiuti": r.get("importo_aiuti_stato", 0),
        "pnrr": r.get("ha_progetti_pnrr", False),
        "importo_pnrr": r.get("importo_pnrr", 0),
        "appalti": r.get("ha_appalti_pubblici", False),
        "n_appalti": r.get("numero_appalti", 0),
        "importo_appalti": r.get("importo_appalti", 0),
        "appalti_riservati": r.get("appalti_riservati", 0),
        "appalti_pnrr": r.get("appalti_pnrr", 0),
        "subappalti": r.get("subappalti", 0),
        "immobili": r.get("patrimonio_immobili", 0),
        "canone": r.get("canone_totale", 0),
    }


def render_scheda_md(scheda, bandi_match, contatti=None):
    """Rende la scheda profilo in markdown, leggibile da chi chiama."""
    r = scheda
    lines = [
        f"# {r['denominazione']}",
        "",
        f"**CF:** {r['codice_fiscale']}  ·  **Sezione:** {r['sezione']}  ·  "
        f"**Sede:** {r['comune']} ({r['provincia']})  ·  **Iscritto:** {r['data_iscrizione'] or '?'}",
        "",
        f"## Capacità progettuale: **{r['capacita'] or 'sconosciuta'}**",
        "",
        "| Segnale | Dettaglio |",
        "|---|---|",
    ]
    segnali = [
        (f"5x1000 2025", fmt_euro(r['5x1000_2025']) if r['5x1000_2025'] else "—"),
        (f"5x1000 totale", fmt_euro(r['5x1000_totale']) if r['5x1000_totale'] else "—"),
        ("Grant UE", f"{fmt_euro(r['importo_ue'])}" if r['ue'] else "—"),
        ("Aiuti di Stato", f"{fmt_euro(r['importo_aiuti'])}" if r['aiuti_stato'] else "—"),
        ("PNRR", f"{fmt_euro(r['importo_pnrr'])}" if r['pnrr'] else "—"),
        ("Appalti ANAC", f"{r['n_appalti']} gare, {fmt_euro(r['importo_appalti'])}" if r['appalti'] else "—"),
        ("Appalti riservati", str(r['appalti_riservati']) if r['appalti_riservati'] else "—"),
        ("Appalti PNRR", str(r['appalti_pnrr']) if r['appalti_pnrr'] else "—"),
        ("Subappalti", str(r['subappalti']) if r['subappalti'] else "—"),
        ("Immobili pubblici", f"{r['immobili']} (canone €{r['canone']:,.0f}/anno)" if r['immobili'] else "—"),
    ]
    for nome, det in segnali:
        lines.append(f"| {nome} | {det} |")
    lines.append("")

    if contatti:
        lines += ["## Contatti", ""]
        if contatti.get("telefono"):
            lines.append(f"- 📞 **{contatti['telefono']}**")
        if contatti.get("sito_web"):
            lines.append(f"- 🌐 {contatti['sito_web']}")
        if contatti.get("indirizzo"):
            lines.append(f"- 📍 {contatti['indirizzo']}")
        if contatti.get("rating"):
            lines.append(f"- ⭐ {contatti['rating']} ({contatti.get('totale_recensioni', '?')} recensioni)")
        lines.append("")

    if bandi_match:
        lines += ["## Bandi dove il nostro matching la segnala", ""]
        for b in sorted(bandi_match, key=lambda x: -x["score"])[:6]:
            urg = "🔴" if b["gg"] <= 30 else "🟡" if b["gg"] <= 60 else "🟢"
            lines.append(f"- {urg} **{b['bando']}** — {b['ente']} — score {b['score']} — scad. {b['scadenza']} ({b['gg']}gg)")
            if b.get("budget"):
                lines.append(f"  - Budget: {fmt_euro(b['budget'])}")
            lines.append(f"  - Perché: {b['motivo']}")
        lines.append("")

    lines += [
        "## Domande da fare al colloquio",
        "",
        "*(seleziona le 3-4 più rilevanti — vedi questionario completo)*",
        "",
    ]
    return "\n".join(lines)


QUESTIONARIO = """# Questionario di scoperta — pilota outreach

*Da usare come traccia per il colloquio. Non è un modulo da compilare: lo
scopo è capire i bisogni reali dell'ETS, non vendere nulla. Le domande che
riportano i nostri dati servono ad aprire la conversazione.*

## A. Chi sei

1. Cosa fa l'ente, da quanto esiste, con quanti volontari/lavoratori?
2. Quali sono le 2-3 attività principali e chi raggiungono?
3. Com'è organizzata la parte amministrativa (chi segue bandi, contabilità, 5x1000)?

## B. Finanziamenti e bandi

4. Come scoprite oggi i bandi a cui candidarvi? (newsletter, CSV, passaparola, nessuno)
5. Quali fonti di finanziamento usate? (contributi privati, 5x1000, bandi di fondazioni, bandi pubblici, gare, UE)
6. Su un totale di [importo 5x1000], quanto vi aiuta davvero?
7. Vi siete mai candidati a una gara pubblica (ANAC)? Se no, perché?

## C. Capacità progettuale

8. Quanto tempo dedicate alla progettazione? C'è qualcuno dedicato?
9. Quando un bando non lo fate, qual è il motivo principale? (tempo, competenze, requisiti, budget, partner)
10. Avete mai collaborato con altri ETS su un progetto? Con chi?

## D. Dati e strumenti

11. Quali decisioni vi piacerebbe prendere con più dati? (es. "dove sono i miei beneficiari", "quanto valgo vs altri enti", "quali bandi sono fattibili")
12. Usate strumenti digitali per gestire attività, soci, contabilità? Quali?

## E. Come possiamo aiutarvi (apertura)

13. Se aveste un servizio che vi dice "questi bandi sono fattibili per te" o
    "la tua capacità rispetto a enti simili", cosa vi servirebbe davvero?
14. Cosa è più urgente oggi per l'ente? (risorse, persone, visibilità, dati, rete)
15. Conoscete il [CSV di riferimento]? Con che rapporto siete?

---
**Risposte da riportare in:** `data/reporting/outreach/{TERRITORIO}/colloqui/{cf}.md`
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description="Kit di scoperta per pilota outreach")
    parser.add_argument("territorio", help="Sigla provincia (es. BO)")
    parser.add_argument("--n", type=int, default=10, help="Dimensione campione (default 10)")
    parser.add_argument("--seed", type=int, default=42, help="Seed campionamento (default 42)")
    parser.add_argument("--enrich", action="store_true", help="Arricchisci contatti con Google Places")
    parser.add_argument("--csv-only", action="store_true", help="Solo shortlist CSV, niente schede")
    args = parser.parse_args(argv)

    territorio = args.territorio.upper()
    con = duckdb.connect()

    print(f"🏘  Campione per {territorio}: {args.n} ETS (seed {args.seed})")
    campione = campiona(con, territorio, n=args.n, seed=args.seed)
    if not campione:
        print(f"❌ Nessun ETS trovato per {territorio}")
        sys.exit(1)

    # Shortlist CSV
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    oggi = datetime.now().strftime("%Y%m%d")
    csv_path = OUTPUT_DIR / f"outreach-{territorio}-{oggi}.csv"

    contatti_cache = {}

    if args.enrich:
        from lib.places import cerca_ets
        print("🔍 Arricchimento Google Places (può essere lento)...")
        for i, e in enumerate(campione):
            gp = cerca_ets(e["denominazione"], e["comune"])
            if gp:
                contatti_cache[e["codice_fiscale"]] = gp
            if (i + 1) % 5 == 0:
                print(f"  ⌛ {i+1}/{len(campione)}")

    rows = []
    import math
    for e in campione:
        s = scheda_ets(con, e)
        gp = contatti_cache.get(e["codice_fiscale"], {})
        rows.append({
            "cf": s["codice_fiscale"],
            "denominazione": s["denominazione"],
            "comune": s["comune"],
            "sezione": s["sezione"],
            "capacita": s["capacita"],
            "importo_5x1000_2025": s["5x1000_2025"] if s["5x1000_2025"] and not math.isnan(s["5x1000_2025"]) else "",
            "n_bandi_match": len(e.get("bandi_match", [])),
            "telefono": gp.get("telefono", ""),
            "sito_web": gp.get("sito_web", ""),
            "indirizzo": gp.get("indirizzo", ""),
            "rating": gp.get("rating", ""),
            "google_url": f"https://www.google.com/maps/place/?q=place_id:{gp['place_id']}" if gp.get("place_id") else "",
        })
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"✅ Shortlist: {csv_path}")

    if args.csv_only:
        con.close()
        return

    # Schede + questionario
    out_dir = REPORTING / territorio
    coll_dir = out_dir / "colloqui"
    coll_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "questionario.md").write_text(QUESTIONARIO.replace("{TERRITORIO}", territorio), encoding="utf-8")

    for e in campione:
        s = scheda_ets(con, e)
        gp = contatti_cache.get(e["codice_fiscale"])
        md = render_scheda_md(s, e.get("bandi_match", []), contatti=gp)
        slug = f"{s['codice_fiscale']}_{s['denominazione'][:30]}".replace(" ", "_").replace("/", "_")
        scheda_path = out_dir / f"{slug}.md"
        scheda_path.write_text(md, encoding="utf-8")
        print(f"  📄 {scheda_path.name}")

    # Riepilogo campione
    print()
    print(f"📋 Riepilogo campione ({len(campione)} ETS):")
    for e in campione:
        n_bandi = len(e.get("bandi_match", []))
        print(f"  · {e['capacita_progettuale'] or 'sconosciuta':12s} {e['sezione'][:30]:30s} {e['comune']:15s} {e['denominazione'][:40]}{' — ' + str(n_bandi) + ' bandi' if n_bandi else ''}")

    print()
    print(f"📚 Deliverable in {out_dir}:")
    print(f"   · {len(campione)} schede profilo (una per ETS)")
    print(f"   · questionario.md — traccia colloquio")
    print(f"   · colloqui/ — da compilare dopo ogni incontro")

    con.close()


if __name__ == "__main__":
    main()
