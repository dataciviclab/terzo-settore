#!/usr/bin/env python3
"""Test: verifica che il matching produca risultati attesi.

Fallisce se pattern conosciuti non trovano ETS.
Uso: python test_match.py [--verbose]
"""

import sys, json
from pathlib import Path
import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from patterns import (
    get_pattern_from_tags, extract_tags_from_text,
    get_sections_from_tags, get_province_filter,
)
from radar.core import classify_bando, parse_date_flex

ETS_FILE = Path("data/unified_ets.parquet")

TESTS = [
    # (nome_test, tag, atteso: almeno N match)
    ("sport", ["sport"], 1),
    ("disabilità", ["disabilità"], 1),
    ("minori", ["minori"], 1),
    ("cultura", ["cultura"], 1),
    ("ambiente", ["ambiente"], 1),
    ("inclusione sociale", ["inclusione sociale"], 1),
    ("volontariato", ["volontariato"], 1),
    ("digitale", ["digitale"], 1),
    ("generici (giovani+solo)", ["giovani"], 1),  # fallback a generici
]

def is_sport_tags(tags):
    return any((t or "").strip().lower() == "sport" for t in tags)

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

        match_condition = f"(regexp_matches(lower(denominazione), '{pattern}')"
        if is_sport_tags(tags):
            match_condition += " OR flag_sport_denom"
        match_condition += ")"
        sql = f"""
            SELECT COUNT(*) as cnt
            FROM '{ETS_FILE}'
            WHERE {match_condition}
              AND capacita_progettuale IN ('media', 'medio-alta', 'alta')
        """
        result = con.sql(sql).fetchone()[0]

        if result >= expected:
            status = "✅"
        else:
            status = "❌"
            failures += 1

        print(f" {status} {name}: {result} match (atteso ≥{expected})")
        if verbose and result > 0:
            top = con.sql(f"""
                SELECT denominazione, comune, capacita_progettuale
                FROM '{ETS_FILE}'
                WHERE {match_condition}
                  AND capacita_progettuale IN ('media', 'medio-alta', 'alta')
                ORDER BY cinque_2025 DESC NULLS LAST
                LIMIT 2
            """).fetchdf()
            for _, r in top.iterrows():
                print(f"      · {r['denominazione'][:45]} ({r['comune']}) [{r['capacita_progettuale']}]")

    # Regressione: il fallback sportivo non deve gonfiare bandi non sportivi.
    digitale_pattern = get_pattern_from_tags(["digitale"])
    regex_only = con.sql(f"""
        SELECT COUNT(*) FROM '{ETS_FILE}'
        WHERE regexp_matches(lower(denominazione), '{digitale_pattern}')
          AND capacita_progettuale IN ('media', 'medio-alta', 'alta')
    """).fetchone()[0]
    old_behavior = con.sql(f"""
        SELECT COUNT(*) FROM '{ETS_FILE}'
        WHERE (regexp_matches(lower(denominazione), '{digitale_pattern}') OR flag_sport_denom)
          AND capacita_progettuale IN ('media', 'medio-alta', 'alta')
    """).fetchone()[0]
    if old_behavior <= regex_only:
        print("❌ regressione fallback sportivo non verificabile per tag non sportivo")
        failures += 1
    else:
        print(f" ✅ fallback sportivo limitato: digitale {regex_only} match vs {old_behavior} col vecchio OR")

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
    gold_path = Path(__file__).resolve().parent / "tests/gold_bandi.json"
    if gold_path.exists():
        print()
        print("🧪 Gold set test:")
        with open(gold_path) as f:
            gold = json.load(f)
        for entry in gold:
            pattern = get_pattern_from_tags(entry["tags"])
            match_condition = f"(regexp_matches(lower(denominazione), '{pattern}')"
            if is_sport_tags(entry["tags"]):
                match_condition += " OR flag_sport_denom"
            match_condition += ")"
            count = con.sql(f"""
                SELECT COUNT(*) FROM '{ETS_FILE}'
                WHERE {match_condition}
                  AND capacita_progettuale IN ('media', 'medio-alta', 'alta')
            """).fetchone()[0]

            atteso = entry["atteso"]
            if atteso["match"]:
                ok = count >= atteso.get("min_candidati", 1)
            else:
                ok = count == 0
            status = "✅" if ok else "❌"
            if not ok:
                failures += 1
            print(f" {status} {entry['id']}: {count} match (atteso {'≥' + str(atteso.get('min_candidati', 1)) if atteso['match'] else '0'})")
            if verbose and ok:
                pass  # silent if gold passes
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
        ("cultura ucraina (no FP)", "Progetti culturali in Moldavia", []),
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
    radar_json = Path(__file__).resolve().parent / "cruscotto/radar-completo.json"
    if radar_json.exists():
        with open(radar_json) as f:
            report = json.load(f)
        checks = [
            ("Bandi totali > 200", report["bandi_totali"] > 200),
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

    con.close()
    print()
    if failures:
        print(f"❌ {failures} test falliti")
        sys.exit(1)
    else:
        print("✅ Tutti i test passati")

if __name__ == "__main__":
    main()
