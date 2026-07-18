#!/usr/bin/env python3
"""Diagnostica matching: misura il contributo di ogni componente.

Per ogni componente del matching, risponde a:
1. Quanti ETS matcha DA SOLO? (contribuzione unica)
2. Senza questo componente, quanti ETS si perdono? (dipendenza)
3. Quanto incide sullo score medio? (impatto)

Uso:
    python3 -m tsi.matching.diagnose
    python3 -m tsi.matching.diagnose --bando "BPER"
    python3 -m tsi.matching.diagnose --tag sport --output report.json
"""

from __future__ import annotations
import argparse
import json
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import duckdb

from tsi.matching.engine import (
    ETS_FILE,
    MATCH_ETS_SQL,
    load_bandi,
    normalise_bando,
    parse_date_flex,
    classify_bando,
    get_pattern_from_tags,
    get_sections_from_tags,
    get_province_filter,
    is_sport_bando,
    is_missing,
)
from tsi.matching.patterns import TAG_PATTERN


# ── Componenti da testare ─────────────────────────────────────────────

COMPONENTI = {
    "pattern": {
        "nome": "Keyword denominazione",
        "descrizione": "Match per keyword nel nome ETS",
        "peso_max": 60,
    },
    "sezione": {
        "nome": "Sezione RUNTS",
        "descrizione": "Match per pertinenza sezione (ODV, APS, IS...)",
        "peso_max": 25,
    },
    "sport_flag": {
        "nome": "Sport flag",
        "descrizione": "Flag sport_denom per ETS sportivi",
        "peso_max": 15,
    },
    "capacita": {
        "nome": "Capacità progettuale",
        "descrizione": "Filtro soglia: solo media, medio-alta, alta",
        "peso_max": 20,
    },
    "bonus_5x1000": {
        "nome": "Bonus 5x1000",
        "descrizione": "Punteggio aggiuntivo per raccolta fondi",
        "peso_max": 15,
    },
    "bonus_anac": {
        "nome": "Bonus ANAC",
        "descrizione": "Punteggio per appalti pubblici vinti",
        "peso_max": 10,
    },
    "bonus_ue": {
        "nome": "Bonus Grant UE",
        "descrizione": "Punteggio per grant europei",
        "peso_max": 8,
    },
    "bonus_pnrr": {
        "nome": "Bonus PNRR",
        "descrizione": "Punteggio per progetti PNRR",
        "peso_max": 5,
    },
    "bonus_sezione_legacy": {
        "nome": "Bonus sezione legacy",
        "descrizione": "Bonus extra per ODV/APS/IS su tag specifici",
        "peso_max": 5,
    },
    "filtro_geografico": {
        "nome": "Filtro geografico",
        "descrizione": "Restrizione a province del territorio",
        "peso_max": 0,  # non è un bonus, è un filtro
    },
}

# Map component → SQL modification needed to disable it
# Each entry: (match_condition_change, score_change, where_change)
# If None, the component cannot be disabled via SQL (only via scoring)


def match_con_componenti_disabilitati(
    con, pattern, tags, territorio=None, limit=1000, disabilita=None
):
    """Esegue match con alcuni componenti disabilitati.

    disabilita: set di stringhe (es. {'pattern', 'sezione', 'bonus_anac'})
    """
    disabilita = disabilita or set()
    sections = get_sections_from_tags(tags)
    sezioni_quote = ", ".join(f"'{s}'" for s in sections) if sections else "''"

    sport_fallback = is_sport_bando(tags)

    # ── Match condition ──
    match_condition_parts = []
    if "pattern" not in disabilita and pattern:
        match_condition_parts.append(f"regexp_matches(lower(denominazione), '{pattern}')")
    if "sport_flag" not in disabilita and sport_fallback:
        match_condition_parts.append("flag_sport_denom")
    if "sezione" not in disabilita and sections:
        match_condition_parts.append(f"sezione IN ({sezioni_quote})")

    if not match_condition_parts:
        return con.sql("SELECT * FROM (SELECT NULL as codice_fiscale) WHERE 1=0").fetchdf()

    match_condition = " OR ".join(match_condition_parts)

    # ── Sezione match bool (per score CASE) ──
    sez_match_bool = "FALSE"
    if "sezione" not in disabilita and sections:
        sez_match_bool = f"sezione IN ({sezioni_quote})"

    # ── Filtro geografico ──
    province_filter = ""
    if "filtro_geografico" not in disabilita:
        province_filtro = get_province_filter(territorio or [])
        if province_filtro:
            prov_quote = ", ".join(f"'{p}'" for p in province_filtro)
            province_filter = f"AND provincia IN ({prov_quote})"

    # ── Build score ──
    score_parts = []

    def _cond(cond, val, default=0):
        """Aggiunge condizione se abilitata, altrimenti default."""
        if cond:
            score_parts.append(f"+ {val}")
        else:
            score_parts.append(f"+ {default}")

    # Pattern match
    _cond("pattern" not in disabilita and pattern,
          f"CASE WHEN regexp_matches(lower(denominazione), '{pattern}') THEN 60 ELSE 0 END",
          0)

    # Sezione match
    _cond("sezione" not in disabilita,
          f"CASE WHEN {sez_match_bool} THEN 25 ELSE 0 END",
          0)

    # Sport bonus
    _cond("sport_flag" not in disabilita and sport_fallback,
          "CASE WHEN flag_sport_denom THEN 15 ELSE 0 END",
          0)

    # Capacità (sempre attivo - filtro strutturale)
    score_parts.append(
        "+ CASE capacita_progettuale"
        "  WHEN 'alta' THEN 20 WHEN 'medio-alta' THEN 15 WHEN 'media' THEN 10 ELSE 0 END"
    )

    # 5x1000
    _cond("bonus_5x1000" not in disabilita,
          "CASE WHEN cinque_2025 >= 100000 THEN 15 WHEN cinque_2025 >= 10000 THEN 10 WHEN cinque_2025 > 0 THEN 5 ELSE 0 END",
          0)

    # ANAC
    _cond("bonus_anac" not in disabilita,
          "CASE WHEN importo_appalti >= 10000000 THEN 10 WHEN importo_appalti >= 1000000 THEN 7 WHEN importo_appalti >= 100000 THEN 5 WHEN ha_appalti THEN 3 ELSE 0 END",
          0)

    # Grant UE
    _cond("bonus_ue" not in disabilita,
          "CASE WHEN ha_grant_ue THEN 8 ELSE 0 END",
          0)

    # PNRR
    _cond("bonus_pnrr" not in disabilita,
          "CASE WHEN ha_pnrr THEN 5 ELSE 0 END",
          0)

    # Bonus sezione legacy
    tags_lower = set(t.lower() for t in tags)
    bonus_legacy = []
    if "bonus_sezione_legacy" not in disabilita:
        if "volontariato" in tags_lower:
            bonus_legacy.append("CASE WHEN sezione = 'ORGANIZZAZIONI DI VOLONTARIATO' THEN 5 ELSE 0 END")
        if "sport" in tags_lower:
            bonus_legacy.append("CASE WHEN sezione = 'ASSOCIAZIONI DI PROMOZIONE SOCIALE' THEN 5 ELSE 0 END")
        if "lavoro" in tags_lower or "formazione" in tags_lower:
            bonus_legacy.append("CASE WHEN sezione = 'IMPRESE SOCIALI' THEN 5 ELSE 0 END")
    if bonus_legacy:
        score_parts.append("+ " + " + ".join(bonus_legacy))

    score_sql = " ".join(score_parts)

    sql = MATCH_ETS_SQL.format(
        ets_file=ETS_FILE,
        pattern=pattern or ".*",
        match_condition=match_condition or "1=0",
        sport_bonus="TRUE" if (sport_fallback and "sport_flag" not in disabilita) else "FALSE",
        sez_match_bool=sez_match_bool,
        section_bonus="",
        province_filter=province_filter,
        limit=limit,
    )
    # Replace the score in MATCH_ETS_SQL with our custom score
    sql = sql.replace(
        "(\n              -- Match tematico (0-60) — PESO PRINCIPALE\n"
        "             CASE WHEN regexp_matches(lower(denominazione), '{pattern}') THEN 60 ELSE 0 END",
        f"(\n             {score_parts[0]}",
    )
    # The replacement is tricky. Let me use a simpler approach: raw SQL injection
    # Actually let me just build a custom SQL directly

    # Reset: build SQL from scratch
    sql = f"""
        SELECT codice_fiscale, denominazione, comune, provincia, capacita_progettuale,
               cinque_2025, flag_sport_denom, sezione,
               ha_grant_ue, ha_pnrr, ha_appalti, importo_appalti,
               ({score_sql}) AS score
        FROM '{ETS_FILE}'
        WHERE ({match_condition})
          AND capacita_progettuale IN ('media', 'medio-alta', 'alta')
          {province_filter}
        ORDER BY score DESC, cinque_2025 DESC NULLS LAST
        LIMIT {limit}
    """
    return con.sql(sql).fetchdf()


def diagnostica_bandi(bandi_filter=None, tag_filter=None, verbose=True):
    """Esegue diagnostica sui bandi selezionati."""
    con = duckdb.connect()
    tutti_bandi = load_bandi()

    risultati_bandi = []
    contatori_componenti = Counter()
    contatori_coppie = Counter()

    for b in tutti_bandi:
        titolo, url, scadenza_str, ente, tags, territorio, fonte = normalise_bando(b)
        scadenza, gg_rimasti = parse_date_flex(scadenza_str)
        status, _ = classify_bando(b, scadenza, gg_rimasti)
        if status not in ("attivo", "sportello"):
            continue

        # Filtri
        if bandi_filter and bandi_filter.lower() not in titolo.lower():
            continue
        if tag_filter and tag_filter.lower() not in [t.lower() for t in tags]:
            continue

        pattern = get_pattern_from_tags(tags)
        if not pattern:
            continue

        if verbose:
            print(f"\n📌 {titolo[:60]}")
            print(f"   Tags: {tags} | Territorio: {territorio}")

        # Run FULL match
        df_full = match_con_componenti_disabilitati(
            con, pattern, tags, territorio=territorio, disabilita=set()
        )
        if df_full.empty:
            if verbose:
                print(f"   ❌ Nessun match")
            continue

        totale_full = len(df_full)
        cf_full = set(df_full["codice_fiscale"].tolist())

        # Testa ogni componente: match SENZA quel componente
        contribuzione = {}
        for comp in COMPONENTI:
            df_parz = match_con_componenti_disabilitati(
                con, pattern, tags, territorio=territorio,
                disabilita={comp},
            )
            cf_parz = set(df_parz["codice_fiscale"].tolist()) if not df_parz.empty else set()
            persi = cf_full - cf_parz
            contribuzione[comp] = {
                "totale": len(df_parz),
                "persi": len(persi),
                "percentuale_persi": round(len(persi) / totale_full * 100, 1) if totale_full else 0,
            }

        risultati_bandi.append({
            "titolo": titolo[:60],
            "tags": tags,
            "totale_match": totale_full,
            "contribuzione": contribuzione,
        })

        if verbose:
            print(f"   Totale match: {totale_full}")
            print(f"   Contribuzione componenti:")
            for comp, dati in sorted(contribuzione.items(), key=lambda x: -x[1]["persi"]):
                if dati["persi"] > 0:
                    print(f"     · {COMPONENTI[comp]['nome']:25s}: -{dati['persi']:>4d} ETS ({dati['percentuale_persi']:>5.1f}%)")
                else:
                    print(f"     · {COMPONENTI[comp]['nome']:25s}: nessuna perdita")

        # Analisi motivo_match
        motivo_counts = Counter()
        for _, row in df_full.iterrows():
            motivo = row.get("motivo_match", "")
            motivo_counts[motivo] += 1
        if verbose:
            print(f"   Ripartizione motivo match:")
            for motivo, count in motivo_counts.most_common():
                print(f"     · {motivo:30s}: {count:>4d} ETS")

    con.close()
    return risultati_bandi


def report_sintetico(risultati):
    """Produce report riassuntivo su tutti i bandi analizzati."""
    if not risultati:
        print("\n❌ Nessun risultato")
        return

    print("\n" + "=" * 70)
    print("📊 REPORT DIAGNOSTICA MATCHING")
    print("=" * 70)
    print(f"Bandi analizzati: {len(risultati)}")
    print(f"Match totali (media): {sum(r['totale_match'] for r in risultati) / len(risultati):.0f}")
    print()

    # Aggrega contribuzione per componente
    aggr = {}
    for comp, info in COMPONENTI.items():
        tot_persi = sum(r["contribuzione"][comp]["persi"] for r in risultati)
        tot_match = sum(r["totale_match"] for r in risultati)
        media_persi = tot_persi / len(risultati) if risultati else 0
        media_perc = tot_persi / max(tot_match, 1) * 100
        bandi_con_impatto = sum(1 for r in risultati if r["contribuzione"][comp]["persi"] > 0)
        aggr[comp] = {
            "nome": info["nome"],
            "descrizione": info["descrizione"],
            "persi_tot": tot_persi,
            "media_persi": round(media_persi, 1),
            "media_perc": round(media_perc, 1),
            "bandi_con_impatto": bandi_con_impatto,
            "peso_max": info["peso_max"],
        }

    print(f"{'Componente':30s} {'Persi tot':>10s} {'Media':>8s} {'%media':>8s} {'Bandi':>6s} {'Peso':>6s}")
    print("-" * 70)
    for comp, dati in sorted(aggr.items(), key=lambda x: -x[1]["persi_tot"]):
        print(
            f"{dati['nome']:30s} {dati['persi_tot']:>10d} {dati['media_persi']:>8.1f} "
            f"{dati['media_perc']:>7.1f}% {dati['bandi_con_impatto']:>4d}/{len(risultati):<2d} "
            f"{dati['peso_max']:>4d}pt"
        )

    # Componenti senza impatto
    print()
    zero_impatto = [dati for c, dati in aggr.items() if dati["persi_tot"] == 0]
    if zero_impatto:
        print("⚠️  Componenti con zero impatto:")
        for dati in zero_impatto:
            print(f"   · {dati['nome']} ({dati['descrizione']}) — peso {dati['peso_max']}pt")


def main():
    parser = argparse.ArgumentParser(description="Diagnostica matching")
    parser.add_argument("--bando", help="Filtra per nome bando")
    parser.add_argument("--tag", help="Filtra per tag (es. sport, minori)")
    parser.add_argument("--output", help="Salva report JSON")
    parser.add_argument("--sintetico", action="store_true", help="Solo report finale, non per-bando")
    args = parser.parse_args()

    risultati = diagnostica_bandi(
        bandi_filter=args.bando,
        tag_filter=args.tag,
        verbose=not args.sintetico,
    )

    report_sintetico(risultati)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(risultati, f, indent=2, default=str)
        print(f"\n✅ Report salvato in {args.output}")


if __name__ == "__main__":
    main()
