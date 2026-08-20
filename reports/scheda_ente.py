#!/usr/bin/env python3
"""Scheda ETS on-demand: profilo completo di un ente del Terzo Settore.

Genera una scheda markdown dal mart_ets (profilo) + query live GCS (dettagli per fonte).

Uso:
    python3 reports/scheda_ente.py 02006180364          # 1 ente → data/reporting/schede/
    python3 reports/scheda_ente.py --all                # tutte le schede (lista fissa)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parents[1]
MART_ETS = REPO / "out" / "data" / "mart" / "ets_unified" / "2026" / "ets_unified.parquet"
CLEAN = REPO / "out" / "data" / "clean" / "ets_unified" / "2026" / "ets_unified_2026_clean.parquet"
OUT = REPO / "data" / "reporting" / "schede"
GCS = "https://storage.googleapis.com/dataciviclab-clean"

# ETS di riferimento per test e seed
SEED = [
    ("02006180364", "Fondazione Nazareno"),
]


def fmt_euro(v) -> str:
    if v is None or v == 0:
        return "-"
    return f"€{v:,.0f}"


def fmt_int(v) -> str:
    if v is None or v == 0:
        return "0"
    return f"{int(v):,}".replace(",", ".")


def fmt_bool(v) -> str:
    return "sì" if v else "no"


def fmt_date(v) -> str:
    if v is None:
        return "-"
    return str(v)[:10]


def _query(con: duckdb.DuckDBPyConnection, sql: str) -> list[dict]:
    """Esegue query e restituisce lista di dict. Gestisce errori silenziosamente."""
    try:
        rows = con.execute(sql).fetchall()
        cols = [d[0] for d in con.description]
        return [dict(zip(cols, row)) for row in rows]
    except duckdb.Error:
        return []


def dettaglio_anac(con: duckdb.DuckDBPyConnection, cf: str) -> list[dict]:
    """Ultime 5 gare ANAC. Deduplica per importo+stazione (stesso CIG = stesso importo)."""
    sql = f"""
    SELECT anno, importo, oggetto_gara, stazione_appaltante, appalto_riservato, flag_pnrr
    FROM '{CLEAN}'
    WHERE cf = '{cf}' AND fonte = 'anac' AND oggetto_gara IS NOT NULL
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY ROUND(importo, 0), stazione_appaltante
        ORDER BY anno DESC
    ) = 1
    ORDER BY anno DESC, importo DESC
    LIMIT 5
    """
    return _query(con, sql)


def trend_5x1000(con: duckdb.DuckDBPyConnection, cf: str) -> list[dict]:
    """Evoluzione 5x1000 anno per anno (2023-2025)."""
    sql = f"""
    SELECT anno, importo
    FROM '{CLEAN}'
    WHERE cf = '{cf}' AND fonte = '5x1000'
    ORDER BY anno
    """
    return _query(con, sql)


def dettaglio_rna(con: duckdb.DuckDBPyConnection, cf: str) -> list[dict]:
    """Dettaglio aiuti di stato: soggetto concedente, tipo procedimento, importo."""
    sql = f"""
    SELECT anno, importo_nominale as importo,
           soggetto_concedente, procedimento, cup
    FROM read_parquet([
        '{GCS}/rna_aiuti_stato/2024/rna_aiuti_stato_2024_clean.parquet',
        '{GCS}/rna_aiuti_stato/2025/rna_aiuti_stato_2025_clean.parquet'
    ], union_by_name=true)
    WHERE TRIM(UPPER(REPLACE(codice_fiscale_beneficiario, chr(39), ''))) = '{cf}'
    ORDER BY importo_nominale DESC
    LIMIT 5
    """
    return _query(con, sql)


def dettaglio_fts(con: duckdb.DuckDBPyConnection, cf: str) -> list[dict]:
    """Dettaglio grant UE: programma, importo, flag no-profit/ONG."""
    sql = f"""
    SELECT anno, importo_contrattato as importo,
           budget as programma_ue, flag_no_profit, flag_ong
    FROM read_parquet([
        '{GCS}/fts_eu_grants/2020/fts_eu_grants_2020_clean.parquet',
        '{GCS}/fts_eu_grants/2021/fts_eu_grants_2021_clean.parquet',
        '{GCS}/fts_eu_grants/2022/fts_eu_grants_2022_clean.parquet',
        '{GCS}/fts_eu_grants/2023/fts_eu_grants_2023_clean.parquet',
        '{GCS}/fts_eu_grants/2024/fts_eu_grants_2024_clean.parquet',
        '{GCS}/fts_eu_grants/2025/fts_eu_grants_2025_clean.parquet'
    ], union_by_name=true)
    WHERE TRIM(UPPER(REPLACE(
        CASE WHEN TRIM(beneficiario_partita_iva) LIKE 'IT%'
             THEN SUBSTRING(TRIM(beneficiario_partita_iva), 3)
             ELSE TRIM(beneficiario_partita_iva)
        END, chr(39), ''))) = '{cf}'
      AND TRIM(beneficiario_partita_iva) != '-'
    ORDER BY importo_contrattato DESC
    LIMIT 5
    """
    return _query(con, sql)


def dettaglio_pnrr(con: duckdb.DuckDBPyConnection, cf: str) -> list[dict]:
    """Dettaglio PNRR: programma, missione, importo, stato."""
    sql = f"""
    SELECT programma, missione, fin_totale as importo, misura, stato_progetto
    FROM '{GCS}/pnrr_progetti/2026/pnrr_progetti_2026_clean.parquet'
    WHERE TRIM(UPPER(cf_soggetto_attuatore)) = '{cf}'
    ORDER BY fin_totale DESC
    LIMIT 5
    """
    return _query(con, sql)


def benchmark_territorio(con: duckdb.DuckDBPyConnection, cf: str, r: dict) -> dict | None:
    """Percentile dell'ETS rispetto ai pari del suo comune."""
    comune = r.get("comune")
    if not comune:
        return None
    safe = comune.replace("'", "''")
    sql = f"""
    WITH pari AS (
        SELECT codice_fiscale,
               COALESCE(importo_appalti, 0) as imp_appalti,
               COALESCE(importo_5x1000_totale, 0) as imp_5x1000,
               capacita_progettuale
        FROM '{MART_ETS}'
        WHERE comune = '{safe}'
    ),
    stats AS (
        SELECT count(*) as totale,
               count(CASE WHEN capacita_progettuale IN ('alta', 'medio-alta') THEN 1 END) as attivi,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY imp_appalti) as med_appalti,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY imp_5x1000) as med_5x1000
        FROM pari
    )
    SELECT s.totale as totale_ets_comune, s.attivi as ets_attivi,
           s.med_appalti as mediana_appalti, s.med_5x1000 as mediana_5x1000,
           (SELECT count(*) FROM pari p2 WHERE p2.imp_appalti <= pari.imp_appalti) * 100.0
               / s.totale as pctile_appalti,
           (SELECT count(*) FROM pari p2 WHERE p2.imp_5x1000 <= pari.imp_5x1000) * 100.0
               / s.totale as pctile_5x1000
    FROM pari, stats s
    WHERE pari.codice_fiscale = '{cf}'
    """
    rows = _query(con, sql)
    return rows[0] if rows else None


def scheda(con: duckdb.DuckDBPyConnection, cf: str) -> str | None:
    """Genera scheda markdown completa."""
    sql = f"SELECT * FROM '{MART_ETS}' WHERE codice_fiscale = '{cf}'"
    row = con.execute(sql).fetchone()
    if row is None:
        return None
    cols = [c[0] for c in con.description]
    r = dict(zip(cols, row))

    # Query dettaglio per fonte
    gare_anac = dettaglio_anac(con, cf)
    trend_5k = trend_5x1000(con, cf)
    rna_det = dettaglio_rna(con, cf) if r.get('ha_aiuti_stato') else []
    fts_det = dettaglio_fts(con, cf) if r.get('ha_finanziamenti_ue') else []
    pnrr_det = dettaglio_pnrr(con, cf) if r.get('ha_progetti_pnrr') else []
    bench = benchmark_territorio(con, cf, r)

    # ── Header ──
    md = [f"# {r['denominazione'] or r['codice_fiscale']}", ""]
    md += [f"**CF**: `{r['codice_fiscale']}` | **Sezione**: {r['sezione'] or 'n.d.'} | **Iscrizione**: {fmt_date(r['data_iscrizione'])}", ""]
    md += ["| Dato | Valore |", "|---|---|"]
    md += [f"| Comune | {r['comune'] or 'n.d.'} ({r['provincia'] or '—'}, {r['regione'] or '—'}) |"]
    md += [f"| Codice ISTAT | {r['codice_istat'] or 'n.d.'} |"]
    md += [f"| Capacità progettuale | **{r['capacita_progettuale']}** |"]
    if r.get('ha_sport_in_denominazione'):
        md += ["| Tipo rilevato | Sport dilettantistico (da denominazione) |"]

    # ── Benchmark territoriale ──
    if bench and bench.get('totale_ets_comune', 0) > 1:
        md += ["", "### Posizione nel comune", ""]
        md += [f"Tra **{int(bench['totale_ets_comune'])}** ETS di **{r['comune']}** "
               f"({int(bench['ets_attivi'])} attivi con fatti pubblici):"]
        md += [f"- Appalti pubblici: al **{int(bench['pctile_appalti'])}%** "
               f"(mediana comune: {fmt_euro(bench['mediana_appalti'])})"]
        md += [f"- 5x1000: al **{int(bench['pctile_5x1000'])}%** "
               f"(mediana comune: {fmt_euro(bench['mediana_5x1000'])})"]

    # ── Finanziamenti ──
    md += ["", "## Finanziamenti", "", "| Fonte | Presenza | Importo | Dettaglio |", "|---|---|---|---|"]
    md += [f"| 5x1000 (2025) | {fmt_bool(r['ha_5x1000'])} | {fmt_euro(r['importo_5x1000_2025'])} | {fmt_int(r['anni_5x1000'])} anni |"]
    md += [f"| 5x1000 (totale) | — | {fmt_euro(r['importo_5x1000_totale'])} | — |"]
    md += [f"| Grant UE | {fmt_bool(r['ha_finanziamenti_ue'])} | {fmt_euro(r['importo_ue'])} | {fmt_int(r['progetti_ue'])} progetti |"]
    md += [f"| Aiuti di Stato | {fmt_bool(r['ha_aiuti_stato'])} | {fmt_euro(r['importo_aiuti_stato'])} | {fmt_int(r['progetti_aiuti_stato'])} progetti |"]
    md += [f"| PNRR | {fmt_bool(r['ha_progetti_pnrr'])} | {fmt_euro(r['importo_pnrr'])} | {fmt_int(r['progetti_pnrr'])} progetti |"]

    # Trend 5x1000
    if trend_5k:
        parts = [f"{t['anno']}: {fmt_euro(t['importo'])}" for t in trend_5k]
        md += ["", f"**Trend 5x1000**: {' → '.join(parts)}"]

    # Dettaglio RNA
    if rna_det:
        md += ["", "### Dettaglio Aiuti di Stato", "",
               "| Anno | Importo | Soggetto concedente | Procedimento |", "|---|---|---|---|"]
        for d in rna_det:
            concedente = (d.get('soggetto_concedente') or '-')[:45]
            proc = (d.get('procedimento') or '-')[:25]
            md += [f"| {d.get('anno', '-')} | {fmt_euro(d.get('importo'))} | {concedente} | {proc} |"]

    # Dettaglio FTS/UE
    if fts_det:
        md += ["", "### Dettaglio Grant UE", "",
               "| Anno | Importo | Programma | No-profit | ONG |", "|---|---|---|---|---|"]
        for d in fts_det:
            prog = (d.get('programma_ue') or '-')[:35]
            md += [f"| {d.get('anno', '-')} | {fmt_euro(d.get('importo'))} | {prog} | "
                   f"{fmt_bool(d.get('flag_no_profit'))} | {fmt_bool(d.get('flag_ong'))} |"]

    # Dettaglio PNRR
    if pnrr_det:
        md += ["", "### Dettaglio PNRR", "",
               "| Programma | Missione | Importo | Stato |", "|---|---|---|---|"]
        for d in pnrr_det:
            prog = (d.get('programma') or '-')[:30]
            miss = (d.get('missione') or '-')[:25]
            stato = (d.get('stato_progetto') or '-')[:20]
            md += [f"| {prog} | {miss} | {fmt_euro(d.get('importo'))} | {stato} |"]

    # ── Appalti Pubblici ──
    md += ["", "## Appalti Pubblici (ANAC)", ""]
    md += ["I dati derivano da **ANAC Aggiudicatari** (contratti vinti) e **ANAC Partecipanti** (gare a cui ha partecipato).",
           "L'importo è il valore del contratto diviso per il numero di aggiudicatari sullo stesso CIG.", ""]
    md += ["| Dato | Valore |", "|---|---|"]
    md += [f"| Contratti vinti (CIG) | {fmt_int(r['numero_appalti'])} |"]
    md += [f"| Importo totale aggiudicato | {fmt_euro(r['importo_appalti'])} |"]
    md += [f"| Gare a cui ha partecipato | {fmt_int(r['gare_partecipate'])} | (incluse quelle non vinte)"]
    md += [f"| Appalti riservati | {fmt_int(r['appalti_riservati'])} |"]
    md += [f"| Appalti PNRR | {fmt_int(r['appalti_pnrr'])} |"]
    md += [f"| Subappalti ricevuti | {fmt_int(r['subappalti'])} |"]

    # Ultime aggiudicazioni ANAC
    if gare_anac:
        md += ["", "### Top aggiudicazioni", "", "| Anno | Importo | Oggetto | Stazione appaltante |", "|---|---|---|---|"]
        for g in gare_anac[:5]:
            oggetto = (g.get('oggetto_gara') or '-')[:60]
            stazione = (g.get('stazione_appaltante') or '-')[:40]
            md += [f"| {g.get('anno', '-')} | {fmt_euro(g.get('importo'))} | {oggetto} | {stazione} |"]

    # ── Patrimonio ──
    md += ["", "## Patrimonio Immobiliare", "", "| Dato | Valore |", "|---|---|"]
    md += [f"| Immobili pubblici in uso | {fmt_int(r['patrimonio_immobili'])} |"]
    md += [f"| Canone totale | {fmt_euro(r['canone_totale'])} |"]

    md += ["", "_Fonte: RUNTS + Lab (ANAC/ADE/FTS/RNA/PNRR/MEF). Generata da `reports/scheda_ente.py` on-demand._"]
    return "\n".join(md)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Scheda ETS on-demand")
    ap.add_argument("cfs", nargs="*", help="Codici fiscali da schedulare")
    ap.add_argument("--all", action="store_true", help="genera tutte le schede del seed")
    args = ap.parse_args(argv)

    cfs = args.cfs
    if args.all:
        cfs = [cf for cf, _ in SEED]

    if not cfs:
        ap.error("serve almeno un CF o --all")

    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("SET memory_limit='1GB'")

    for cf in cfs:
        md = scheda(con, cf)
        if md is None:
            print(f"  ⚠️  CF {cf}: nessuna riga trovata")
            continue
        target = OUT / f"{cf}.md"
        target.write_text(md)
        print(f"  scheda scritta: {target}")
    con.close()
    return 0


if __name__ == "__main__":
    main()
