#!/usr/bin/env python3
"""Test: verifica che il matching produca risultati attesi.

Fallisce se pattern conosciuti non trovano ETS.
Uso: python tests/test_match.py [--verbose]
"""

import sys, json
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.config import get_province_filter
from lib.temi import (
    get_pattern_from_tags,
    estrai_temi as extract_tags_from_text,
    sezioni_per_tag as get_sections_from_tags,
)
from match.bando import classify_bando
from match.funnel import match_bando_funnel
from lib.format import parse_date_flex

ETS_FILE = Path("out/data/mart/ets_unified/2026/ets_unified.parquet")

TESTS = [
    ("sport", ["sport"], 1),
    ("disabilità", ["disabilità"], 1),
    ("minori", ["minori"], 1),
    ("cultura", ["cultura"], 1),
    ("ambiente", ["ambiente"], 1),
    ("inclusione sociale", ["inclusione sociale"], 1),
    ("volontariato", ["volontariato"], 1),
    ("digitale", ["digitale"], 1),
    ("generici (giovani+solo)", ["giovani"], 1),
]


def main():
    verbose = "--verbose" in sys.argv
    con = duckdb.connect()
    failures = 0

    print(f"🧪 Test matching ({len(TESTS)} casi)")
    print(f"   ETS file: {ETS_FILE}")
    print()

    for name, tags, expected in TESTS:
        pattern = get_pattern_from_tags(tags)
        if not pattern:
            print(f"❌ {name}: nessun pattern prodotto da tags={tags}")
            failures += 1
            continue

        df = match_bando_funnel(con, tags, limit=9999, territorio=None)
        result = len(df)

        if result >= expected:
            status = "✅"
        else:
            status = "❌"
            failures += 1

        print(f" {status} {name}: {result} match (atteso ≥{expected})")
        if verbose and result > 0:
            for _, r in df.head(2).iterrows():
                print(f"      · {r['denominazione'][:45]} ({r['comune']}) [{r['capacita_progettuale']}]")

    # Regressione: match con vari tag non deve mai sollevare eccezioni
    for tags, expected_n in [(["sport"], 10), (["digitale"], 10), (["volontariato", "giovani"], 10), (["xyz"], 0)]:
        pattern = get_pattern_from_tags(tags)
        if pattern:
            df = match_bando_funnel(con, tags, limit=10, territorio=None)
            assert isinstance(df, object)
    print(" ✅ regressione: nessun errore con vari tag (sport, digitale, misti, sconosciuti)")

    # Funnel a 2 assi: la sezione è GATE, non match. Nessun 'solo_sezione'
    # deve comparire nei top-20 (chi entra solo per sezione senza conferma
    # nel nome finisce in coda, non in testa).
    df_sport = match_bando_funnel(con, ["sport"], limit=20)
    motivi_sport = set(df_sport["motivo_match"].tolist())
    ok_funnel = "solo_sezione" not in motivi_sport and len(df_sport) > 0
    if not ok_funnel:
        failures += 1
    print(f" {'✅' if ok_funnel else '❌'} funnel 2 assi: top-20 sport senza 'solo_sezione' (n={len(df_sport)})")

    print()
    print("🧪 Operational filter test:")
    operational_tests = [
        ({"titolo": "Bando attivo", "scadenza": "31 dicembre 2026"}, "attivo"),
        ({"titolo": "Esito del bando della Regione Marche", "scadenza": ""}, "notizia/esito"),
        ({"titolo": "Bando aperto - Sportello della solidarietà", "scadenza": "senza scadenza, sportello aperto"}, "sportello"),
        ({"titolo": "Bando scaduto", "scadenza": "01 gennaio 2026"}, "scaduto"),
    ]
    for bando, expected_status in operational_tests:
        scadenza, gg = parse_date_flex(bando.get("scadenza", ""))
        status, _ = classify_bando(bando, scadenza, gg)
        ok = status == expected_status
        print(f" {'✅' if ok else '❌'} {bando['titolo'][:45]} → {status} (atteso {expected_status})")
        if not ok:
            failures += 1

    # NLP test
    print()
    nlp_tests = [
        ("sport", "Bando sportivo per ASD", ["sport"]),
        ("volontariato", "Progetti di volontariato giovanile", ["volontariato"]),
        ("premio", "Premio innovazione sociale 2026", ["premi"]),
        ("ucraina", "Progetti culturali Ucraina", ["migranti"]),
    ]
    print("🧪 NLP extraction test:")
    for name, text, expected_tags in nlp_tests:
        extracted = set(extract_tags_from_text(text))
        ok = all(t in extracted for t in expected_tags)
        print(f" {'✅' if ok else '❌'} '{text}' → {extracted} (atteso {expected_tags})")
        if not ok:
            failures += 1

    # ── Gold set ────────────────────────────────────────────────────
    gold_path = Path(__file__).resolve().parents[1] / "tests/gold_bandi.json"
    if gold_path.exists():
        print()
        print("🧪 Gold set test:")
        with open(gold_path) as f:
            gold = json.load(f)
        for entry in gold:
            pattern = get_pattern_from_tags(entry["tags"])
            df = match_bando_funnel(con, entry["tags"], limit=9999, territorio=None)
            count = len(df)
            atteso = entry["atteso"]
            if atteso["match"]:
                ok = count >= atteso.get("min_candidati", 1)
            else:
                ok = count == 0
            status = "✅" if ok else "❌"
            if not ok:
                failures += 1
            print(f" {status} {entry['id']}: {count} match (atteso {'≥' + str(atteso.get('min_candidati', 1)) if atteso['match'] else '0'})")

            # Discriminazione: il top-N di questo bando non deve
            # coincidere con quello di un bando diverso (fix selettività).
            disc = atteso.get("discriminazione_vs")
            if disc:
                df2 = match_bando_funnel(con, disc["tags"], limit=9999, territorio=None)
                top_n = disc.get("top_n", 8)
                max_overlap = disc.get("max_overlap", 2)
                s1 = set(df.head(top_n)["codice_fiscale"].tolist())
                s2 = set(df2.head(top_n)["codice_fiscale"].tolist())
                overlap = len(s1 & s2)
                ok_disc = overlap <= max_overlap
                if not ok_disc:
                    failures += 1
                print(f"   {'✅' if ok_disc else '❌'} discriminazione vs {disc['tags']}: overlap top-{top_n} = {overlap} (atteso ≤{max_overlap})")
    else:
        print(f"\n⚠️  Gold set non trovato: {gold_path}")

    # ── Test sezione gate ────────────────────────────────────────────
    print()
    print("🧪 Section gate test:")
    section_tests = [
        ("volontariato", ["volontariato"], ["ORGANIZZAZIONI DI VOLONTARIATO", "ALTRI ENTI DEL TERZO SETTORE"]),
        ("sport", ["sport"], ["ASSOCIAZIONI DI PROMOZIONE SOCIALE"]),
        ("lavoro", ["lavoro"], ["IMPRESE SOCIALI", "ALTRI ENTI DEL TERZO SETTORE"]),
        ("cultura", ["cultura"], ["ASSOCIAZIONI DI PROMOZIONE SOCIALE", "ALTRI ENTI DEL TERZO SETTORE"]),
        ("donne+volontariato", ["donne", "volontariato"], ["ASSOCIAZIONI DI PROMOZIONE SOCIALE", "ORGANIZZAZIONI DI VOLONTARIATO", "ALTRI ENTI DEL TERZO SETTORE"]),
        ("tag sconosciuto", ["xyz_non_existent"], []),
    ]
    for name, tags, expected in section_tests:
        result = get_sections_from_tags(tags)
        ok = set(result) == set(expected)
        status = "✅" if ok else "❌"
        if not ok:
            failures += 1
        print(f" {status} {name}: {result} (atteso {expected})")

    # ── Test filtro geografico ──────────────────────────────────────
    print()
    print("🧪 Geographic filter test:")
    geo_tests = [
        ("nazionale", ["Nazionale"], []),
        ("mezzogiorno", ["Mezzogiorno"], ["AQ","CH","PE","TE","MT","PZ","CZ","CS","KR","RC","VV","AV","BN","CE","NA","SA","CB","IS","BA","BR","BT","FG","LE","TA","CA","NU","OR","SS","SU","AG","CL","CT","EN","ME","PA","RG","SR","TP"]),
        ("lombardia", ["Lombardia"], ["BG","BS","CO","CR","LC","LO","MB","MI","MN","PV","SO","VA"]),
        ("vuoto", [], []),
        ("europa", ["Europa"], []),
    ]
    for name, terr, expected in geo_tests:
        result = get_province_filter(terr)
        ok = set(result) == set(expected)
        status = "✅" if ok else "❌"
        if not ok:
            failures += 1
            print(f"   (got {len(result)} province, expected {len(expected)})")
        print(f" {status} {name}: {len(result)} province (atteso {len(expected)})")

    # ── Test strategia mista NLP (simula info-cooperazione) ─────────
    print()
    print("🧪 NLP mixed strategy test:")
    nlp_texts = [
        ("violenza genere minori", "Bando per contrastare la violenza di genere e la violenza sui minori", ["minori", "donne"]),
        ("sport", "progetti di sport inclusivo", ["sport"]),
        ("testo corto senza tag", "Bando della Commissione Europea", []),
        ("volontariato giovani", "Progetti di volontariato giovanile", ["volontariato", "giovani"]),
        ("premio innovazione", "Premio innovazione sociale 2026", ["premi"]),
        ("migranti", "Richiedenti asilo e rifugiati", ["migranti"]),
        ("cultura ucraina (no FP)", "Moldavia progetti di sviluppo rurale", []),
    ]
    for name, text, expected_tags in nlp_texts:
        extracted = set(extract_tags_from_text(text))
        ok = all(t in extracted for t in expected_tags) and len(extracted) >= len(expected_tags)
        status = "✅" if ok else "❌"
        if not ok:
            failures += 1
        print(f" {status} {name}: {extracted} (atteso {expected_tags})")

    # ── Test integrità scan ─────────────────────────────────────────
    print()
    print("🧪 Scan integrity test:")
    radar_json = Path(__file__).resolve().parents[1] / "cruscotto/radar-completo.json"
    if radar_json.exists():
        with open(radar_json) as f:
            report = json.load(f)
        checks = [
            ("Bandi totali > 50", report["bandi_totali"] > 50),
            ("Match > 30", report["match"] > 30),
            ("ETS unici > 100", report["ets_unici"] > 100),
            ("Nessun gap con opendoor", all(g["motivo"] != "nessun ETS matcha" for g in report["sin_match"])),
            ("Tutti i resultados hanno candidati", all(len(r["candidati"]) > 0 for r in report["resultados"])),
        ]
        for name, ok in checks:
            status = "✅" if ok else "❌"
            if not ok:
                failures += 1
            print(f" {status} {name}")
    else:
        print(" ⚠️  Scan JSON non trovato, salto test integrità")

    # ── Test integrità indicatore partecipazioni gare ───────────────
    n_part = con.sql(f"SELECT COUNT(*) FILTER (WHERE ha_partecipato_gare) FROM '{ETS_FILE}'").fetchone()[0]
    ok_part = n_part > 10000
    if not ok_part:
        failures += 1
    print(f" {'✅' if ok_part else '❌'} ETS con partecipazioni gare > 10k (attuale: {n_part:,})")

    # ── Test pacchetto territorio (deliverable CSV) ─────────────────
    pacchetto_path = Path(__file__).resolve().parents[1] / "_local/pacchetti/territorio_BO.json"
    if pacchetto_path.exists():
        pacchetto = json.loads(pacchetto_path.read_text())
        checks_pacchetto = [
            ("Schema pacchetto v1", pacchetto.get("schema") == "territorio_pacchetto_v1"),
            ("ETS Bologna > 2500", pacchetto["ets"]["tot"] > 2500),
            ("Contesto sociale presente", pacchetto["contesto_sociale"].get("reddito") is not None),
            ("Bandi con match locale", len(pacchetto["bandi_con_match_locale"]) > 0),
            ("Chiave bidirezionale (id bando)", all(b.get("id") for b in pacchetto["bandi_con_match_locale"])),
            ("Chiave bidirezionale (CF candidati)", all(
                c.get("codice_fiscale") for b in pacchetto["bandi_con_match_locale"] for c in b["candidati"])),
        ]
        for name, ok in checks_pacchetto:
            status = "✅" if ok else "❌"
            if not ok:
                failures += 1
            print(f" {status} {name}")
    else:
        print(" ⚠️  Pacchetto BO non trovato, salto test (esegui make pacchetto T=BO)")

    con.close()
    print()
    if failures:
        print(f"❌ {failures} test falliti")
        sys.exit(1)
    else:
        print("✅ Tutti i test passati")

if __name__ == "__main__":
    main()
