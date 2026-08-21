import json
from pathlib import Path

import pytest

from lib.config import get_province_filter
from lib.format import parse_date_flex
from lib.temi import (
    estrai_temi as extract_tags_from_text,
    get_pattern_from_tags,
    sezioni_per_tag as get_sections_from_tags,
)
from match.bando import classify_bando
from match.funnel import match_bando_funnel

ROOT = Path(__file__).resolve().parents[1]
ETS_FILE = ROOT / "out/data/mart/ets_unified/2026/ets_unified.parquet"

MATCH_TESTS = [
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

OPERATIONAL_TESTS = [
    ({"titolo": "Bando attivo", "scadenza": "31 dicembre 2026"}, "attivo"),
    ({"titolo": "Esito del bando della Regione Marche", "scadenza": ""}, "notizia/esito"),
    ({"titolo": "Bando aperto - Sportello della solidarietà", "scadenza": "senza scadenza, sportello aperto"}, "sportello"),
    ({"titolo": "Bando scaduto", "scadenza": "01 gennaio 2026"}, "scaduto"),
]

NLP_TESTS = [
    ("sport", "Bando sportivo per ASD", ["sport"]),
    ("volontariato", "Progetti di volontariato giovanile", ["volontariato"]),
    ("premio", "Premio innovazione sociale 2026", ["premi"]),
    ("ucraina", "Progetti culturali Ucraina", ["migranti"]),
]

SECTION_TESTS = [
    ("volontariato", ["volontariato"], {"ORGANIZZAZIONI DI VOLONTARIATO", "ALTRI ENTI DEL TERZO SETTORE"}),
    ("sport", ["sport"], {"ASSOCIAZIONI DI PROMOZIONE SOCIALE"}),
    ("lavoro", ["lavoro"], {"IMPRESE SOCIALI", "ALTRI ENTI DEL TERZO SETTORE"}),
    ("cultura", ["cultura"], {"ASSOCIAZIONI DI PROMOZIONE SOCIALE", "ALTRI ENTI DEL TERZO SETTORE"}),
    ("donne+volontariato", ["donne", "volontariato"], {"ASSOCIAZIONI DI PROMOZIONE SOCIALE", "ORGANIZZAZIONI DI VOLONTARIATO", "ALTRI ENTI DEL TERZO SETTORE"}),
    ("tag sconosciuto", ["xyz_non_existent"], set()),
]

GEO_TESTS = [
    ("nazionale", ["Nazionale"], set()),
    ("mezzogiorno", ["Mezzogiorno"], {"AQ","CH","PE","TE","MT","PZ","CZ","CS","KR","RC","VV","AV","BN","CE","NA","SA","CB","IS","BA","BR","BT","FG","LE","TA","CA","NU","OR","SS","SU","AG","CL","CT","EN","ME","PA","RG","SR","TP"}),
    ("lombardia", ["Lombardia"], {"BG","BS","CO","CR","LC","LO","MB","MI","MN","PV","SO","VA"}),
    ("vuoto", [], set()),
    ("europa", ["Europa"], set()),
]

NLP_MIXED_TESTS = [
    ("violenza genere minori", "Bando per contrastare la violenza di genere e la violenza sui minori", {"minori", "donne"}),
    ("sport", "progetti di sport inclusivo", {"sport"}),
    ("testo corto senza tag", "Bando della Commissione Europea", set()),
    ("volontariato giovani", "Progetti di volontariato giovanile", {"volontariato", "giovani"}),
    ("premio innovazione", "Premio innovazione sociale 2026", {"premi"}),
    ("migranti", "Richiedenti asilo e rifugiati", {"migranti"}),
    ("cultura ucraina (no FP)", "Moldavia progetti di sviluppo rurale", set()),
]


# ── Matching ────────────────────────────────────────────────────


@pytest.mark.parametrize("name,tags,min_match", MATCH_TESTS, ids=[t[0] for t in MATCH_TESTS])
def test_matching(con, name, tags, min_match):
    pattern = get_pattern_from_tags(tags)
    assert pattern, f"Nessun pattern prodotto da tags={tags}"
    df = match_bando_funnel(con, tags, limit=9999, territorio=None)
    assert len(df) >= min_match, f"{name}: {len(df)} match (atteso ≥{min_match})"


def test_regression_no_crash(con):
    """Match con vari tag non deve mai sollevare eccezioni."""
    for tags in [["sport"], ["digitale"], ["volontariato", "giovani"], ["xyz"]]:
        pattern = get_pattern_from_tags(tags)
        if pattern:
            df = match_bando_funnel(con, tags, limit=10, territorio=None)
            assert isinstance(df, object)


def test_funnel_2_axes(con):
    """La sezione è GATE, non match — nessun 'solo_sezione' nei top-20."""
    df = match_bando_funnel(con, ["sport"], limit=20)
    assert len(df) > 0
    assert "solo_sezione" not in set(df["motivo_match"].tolist())


# ── Operational filter ──────────────────────────────────────────


@pytest.mark.parametrize("bando,expected_status", OPERATIONAL_TESTS,
                         ids=[b["titolo"][:30] for b, _ in OPERATIONAL_TESTS])
def test_operational_filter(bando, expected_status):
    scadenza, gg = parse_date_flex(bando.get("scadenza", ""))
    status, _ = classify_bando(bando, scadenza, gg)
    assert status == expected_status


# ── NLP extraction ──────────────────────────────────────────────


@pytest.mark.parametrize("name,text,expected_tags", NLP_TESTS, ids=[t[0] for t in NLP_TESTS])
def test_nlp_extraction(name, text, expected_tags):
    extracted = set(extract_tags_from_text(text))
    assert all(t in extracted for t in expected_tags)


# ── NLP mixed strategy ──────────────────────────────────────────


@pytest.mark.parametrize("name,text,expected_tags", NLP_MIXED_TESTS, ids=[t[0] for t in NLP_MIXED_TESTS])
def test_nlp_mixed_strategy(name, text, expected_tags):
    extracted = set(extract_tags_from_text(text))
    assert all(t in extracted for t in expected_tags) and len(extracted) >= len(expected_tags)


# ── Section gate ────────────────────────────────────────────────


@pytest.mark.parametrize("name,tags,expected", SECTION_TESTS, ids=[t[0] for t in SECTION_TESTS])
def test_section_gate(name, tags, expected):
    assert set(get_sections_from_tags(tags)) == expected


# ── Geographic filter ───────────────────────────────────────────


@pytest.mark.parametrize("name,territories,expected", GEO_TESTS, ids=[t[0] for t in GEO_TESTS])
def test_geographic_filter(name, territories, expected):
    assert set(get_province_filter(territories)) == expected


# ── Gold set ────────────────────────────────────────────────────


def _load_gold():
    gold_path = ROOT / "tests/gold_bandi.json"
    if not gold_path.exists():
        return []
    with open(gold_path) as f:
        return json.load(f)


GOLD_ENTRIES = _load_gold()


@pytest.mark.parametrize("entry", GOLD_ENTRIES, ids=[e["id"] for e in GOLD_ENTRIES])
def test_gold_set(con, entry):
    df = match_bando_funnel(con, entry["tags"], limit=9999, territorio=None)
    count = len(df)
    atteso = entry["atteso"]
    if atteso["match"]:
        assert count >= atteso.get("min_candidati", 1), f"{entry['id']}: {count} match (atteso ≥{atteso.get('min_candidati', 1)})"
    else:
        assert count == 0, f"{entry['id']}: {count} match (atteso 0)"

    disc = atteso.get("discriminazione_vs")
    if disc:
        df2 = match_bando_funnel(con, disc["tags"], limit=9999, territorio=None)
        top_n = disc.get("top_n", 8)
        max_overlap = disc.get("max_overlap", 2)
        s1 = set(df.head(top_n)["codice_fiscale"].tolist())
        s2 = set(df2.head(top_n)["codice_fiscale"].tolist())
        overlap = len(s1 & s2)
        assert overlap <= max_overlap, f"discriminazione vs {disc['tags']}: overlap top-{top_n} = {overlap} (atteso ≤{max_overlap})"


# ── Scan integrity ──────────────────────────────────────────────


def test_scan_integrity():
    """Verifica il contratto del radar JSON (se esiste)."""
    radar_json = ROOT / "cruscotto/radar-completo.json"
    if not radar_json.exists():
        pytest.skip("radar-completo.json non trovato")
    with open(radar_json) as f:
        report = json.load(f)
    assert report["bandi_totali"] > 50
    assert report["match"] > 30
    assert report["ets_unici"] > 100
    assert all(g["motivo"] != "nessun ETS matcha" for g in report["sin_match"])
    assert all(len(r["candidati"]) > 0 for r in report["resultados"])


# ── ETS partecipazioni gare ─────────────────────────────────────


def test_ets_partecipazioni_gare(con):
    if not ETS_FILE.exists():
        pytest.skip("ETS mart non trovato")
    n_part = con.sql(f"SELECT COUNT(*) FILTER (WHERE ha_partecipato_gare) FROM '{ETS_FILE}'").fetchone()[0]
    assert n_part > 10_000, f"ETS con partecipazioni gare: {n_part:,} (atteso >10k)"


# ── Pacchetto territorio ────────────────────────────────────────


def test_pacchetto_territorio():
    pacchetto_path = ROOT / "_local/pacchetti/territorio_BO.json"
    if not pacchetto_path.exists():
        pytest.skip("pacchetto BO non trovato")
    pacchetto = json.loads(pacchetto_path.read_text())
    assert pacchetto.get("schema") == "territorio_pacchetto_v1"
    assert pacchetto["ets"]["tot"] > 2500
    assert pacchetto["contesto_sociale"].get("reddito") is not None
    assert len(pacchetto["bandi_con_match_locale"]) > 0
    assert all(b.get("id") for b in pacchetto["bandi_con_match_locale"])
    assert all(
        c.get("codice_fiscale")
        for b in pacchetto["bandi_con_match_locale"]
        for c in b["candidati"]
    )
