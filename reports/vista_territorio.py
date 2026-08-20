#!/usr/bin/env python3
"""Vista Territorio: panorama ETS di un comune o provincia.

Uso:
    python3 reports/vista_territorio.py Bologna           # per comune
    python3 reports/vista_territorio.py --prov BO         # per provincia
    python3 reports/vista_territorio.py --regione Emilia-Romagna
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))

from lib.config import ETS_FILE

OUT = ROOT / "data" / "reporting" / "viste_territoriali"


def fmt_euro(v) -> str:
    if v is None or v == 0:
        return "-"
    return f"\u20ac{int(v):,}".replace(",", ".")


def fmt_int(v) -> str:
    if v is None or v == 0:
        return "0"
    return f"{int(v):,}".replace(",", ".")


def fmt_pct(v) -> str:
    if v is None:
        return "-"
    return f"{v:.1f}%"


def _where_clause(comune=None, prov=None, regione=None) -> str:
    if comune:
        return f"WHERE lower(comune) = '{comune.lower().replace(chr(39), '')}'"
    if prov:
        return f"WHERE upper(provincia) = '{prov.upper()}'"
    if regione:
        return f"WHERE lower(regione) = '{regione.lower().replace(chr(39), '')}'"
    return ""


def _query(con, sql):
    try:
        return con.execute(sql).fetchone()
    except Exception:
        return None


def _query_all(con, sql):
    try:
        return con.execute(sql).fetchall()
    except Exception:
        return []


def vista_territorio(con, comune=None, prov=None, regione=None, top_n=10) -> str:
    where = _where_clause(comune, prov, regione)
    if not where:
        return "Specifica un comune, una provincia o una regione."

    # ── Panoramica ──
    pan = _query(con, f"""
        SELECT
            count(*) as totale,
            count(CASE WHEN capacita_progettuale = 'alta' THEN 1 END) as cap_alta,
            count(CASE WHEN capacita_progettuale = 'medio-alta' THEN 1 END) as cap_medio_alta,
            count(CASE WHEN capacita_progettuale = 'media' THEN 1 END) as cap_media,
            count(CASE WHEN capacita_progettuale = 'base' THEN 1 END) as cap_base,
            count(CASE WHEN capacita_progettuale = 'sconosciuta' OR capacita_progettuale IS NULL THEN 1 END) as cap_sconosciuta,
            count(CASE WHEN ha_appalti_pubblici THEN 1 END) as con_appalti,
            count(CASE WHEN ha_5x1000 THEN 1 END) as con_5x1000,
            count(CASE WHEN ha_finanziamenti_ue THEN 1 END) as con_ue,
            count(CASE WHEN ha_progetti_pnrr THEN 1 END) as con_pnrr,
            count(CASE WHEN ha_aiuti_stato THEN 1 END) as con_rna,
            round(avg(CASE WHEN importo_5x1000_2025 > 0 THEN importo_5x1000_2025 END), 0) as media_5x,
            round(sum(importo_appalti), 0) as tot_appalti,
            round(sum(importo_5x1000_totale), 0) as tot_5x
        FROM '{ETS_FILE}' {where}
    """)
    if not pan or pan[0] == 0:
        return f"Nessun ETS trovato per '{comune or prov or regione}'."

    totale = pan[0]
    attivi = pan[1] + pan[2] + pan[3]  # alta + medio-alta + media
    pct_attivi = round(attivi * 100 / totale, 1) if totale else 0
    pct_alta = round((pan[1] + pan[2]) * 100 / totale, 1) if totale else 0

    # Nome territorio
    if comune:
        terr_name = comune.title()
        terr_tipo = "Comune"
        # Trova provincia e regione
        geo = _query(con, f"SELECT DISTINCT provincia, regione FROM '{ETS_FILE}' {where}")
        sub = f" ({geo[0]}, {geo[1]})" if geo else ""
        terr_name += sub
    elif prov:
        terr_name = f"Provincia di {prov.upper()}"
        terr_tipo = "Provincia"
        geo = _query(con, f"SELECT DISTINCT regione FROM '{ETS_FILE}' {where}")
        sub = f" — {geo[0]}" if geo else ""
        terr_name += sub
    else:
        terr_name = regione.title()
        terr_tipo = "Regione"

    md = [f"# \U0001f4cd {terr_name}", ""]

    # ── Panoramica ──
    md += ["## Panoramica ETS", ""]
    md += [f"- **{fmt_int(totale)}** ETS iscritti"]
    md += [f"- **{fmt_int(attivi)}** con capacit\u00e0 nota ({fmt_pct(pct_attivi)})"]
    md += [f"- Capacit\u00e0 medio-alta+: **{fmt_int(pan[1] + pan[2])}** ({fmt_pct(pct_alta)})"]
    md += [""]

    # Distribuzione capacit\u00e0
    md += ["### Distribuzione capacit\u00e0", ""]
    md += ["| Capacit\u00e0 | ETS | % |", "|---|---|---|"]
    for label, val in [("Alta", pan[1]), ("Medio-alta", pan[2]), ("Media", pan[3]),
                       ("Base", pan[4]), ("Sconosciuta", pan[5])]:
        pct = round(val * 100 / totale, 1) if totale else 0
        bar = "\u2588" * max(1, round(pct / 5)) if pct > 0 else ""
        md += [f"| {label} | {fmt_int(val)} | {fmt_pct(pct)} {bar} |"]

    # ── Presenza fonti ──
    md += ["", "### Presenza fonti pubbliche", ""]
    md += ["| Fonte | ETS | % |", "|---|---|---|"]
    for label, val in [("Appalti ANAC", pan[6]), ("5x1000", pan[7]),
                       ("Grant UE", pan[8]), ("PNRR", pan[9]),
                       ("Aiuti di Stato", pan[10])]:
        pct = round(val * 100 / totale, 1) if totale else 0
        md += [f"| {label} | {fmt_int(val)} | {fmt_pct(pct)} |"]

    # ── Indicatori ──
    md += ["", "### Indicatori", ""]
    md += [f"- 5x1000 medio (tra chi lo riceve): **{fmt_euro(pan[11])}**"]
    md += [f"- Importo totale appalti: **{fmt_euro(pan[12])}**"]
    md += [f"- Importo totale 5x1000: **{fmt_euro(pan[13])}**"]

    # ── Top ETS ──
    top = _query_all(con, f"""
        SELECT denominazione, comune, sezione, capacita_progettuale,
               importo_appalti, importo_5x1000_totale
        FROM '{ETS_FILE}' {where}
        ORDER BY
            CASE capacita_progettuale
                WHEN 'alta' THEN 0 WHEN 'medio-alta' THEN 1
                WHEN 'media' THEN 2 ELSE 3 END,
            COALESCE(importo_appalti, 0) + COALESCE(importo_5x1000_totale, 0) DESC
        LIMIT {top_n}
    """)
    if top:
        md += ["", f"## Top {len(top)} ETS per capacit\u00e0", ""]
        md += ["| # | ETS | Comune | Sezione | Capacit\u00e0 | Appalti | 5x1000 |",
               "|---|---|---|---|---|---|---|"]
        for i, r in enumerate(top):
            nome = (r[0] or "-")[:40]
            com = r[1] or "-"
            sez = (r[2] or "-")[:20]
            cap = r[3] or "-"
            md += [f"| {i+1} | {nome} | {com} | {sez} | {cap} | {fmt_euro(r[4])} | {fmt_euro(r[5])} |"]

    # ── Confronto (solo per comune) ──
    if comune:
        confronto = _query(con, f"""
            SELECT regione,
                   round(avg(CASE WHEN importo_5x1000_2025 > 0 THEN importo_5x1000_2025 END), 0) as media_5x_reg,
                   count(*) as tot_reg,
                   count(CASE WHEN capacita_progettuale IN ('alta', 'medio-alta') THEN 1 END) as attivi_reg
            FROM '{ETS_FILE}'
            WHERE regione = (SELECT DISTINCT regione FROM '{ETS_FILE}' {where})
        """)
        if confronto and confronto[0]:
            md += ["", "### Confronto con la regione", ""]
            md += [f"- Region: {confronto[0]} ({fmt_int(confronto[2])} ETS, {fmt_int(confronto[3])} attivi)"]
            md += [f"- 5x1000 medio regionale: {fmt_euro(confronto[1])}"]

    # ── Bandi attivi (se disponibili) ──
    try:
        from match.pipeline import load_bandi
        from match.funnel import match_bando_funnel
        bandi = load_bandi()
        if bandi:
            md += ["", "## Bandi attivi rilevanti", ""]
            md += ["| Bando | ETS compatibili | Scadenza |", "|---|---|---|"]
            for b in bandi[:8]:
                tags = b.get("tag", [])
                testo = " ".join(str(b.get(k, "") or "") for k in
                               ("titolo", "descrizione", "testo_nlp"))
                territorio_val = [prov.upper()] if prov else None
                if comune:
                    territorio_val = None  # nazionale per comune
                try:
                    df = match_bando_funnel(con, tags, limit=10_000_000,
                                            territorio=territorio_val, testo=testo)
                    n = len(df) if not df.empty else 0
                except Exception:
                    n = "?"
                titolo_b = (b.get("titolo") or "-")[:50]
                scad = str(b.get("scadenza") or "-")[:25]
                md += [f"| {titolo_b} | {n} | {scad} |"]
    except Exception:
        pass

    md += ["", "---", "",
           f"_Dati: mart ETS ({fmt_int(totale)} enti). "
           f"Generata da `reports/vista_territorio.py`._"]

    return "\n".join(md)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Vista Territorio — panorama ETS")
    ap.add_argument("territorio", nargs="?", help="Nome comune (es. Bologna)")
    ap.add_argument("--prov", "-p", help="Sigla provincia (es. BO)")
    ap.add_argument("--regione", "-r", help="Nome regione (es. Emilia-Romagna)")
    ap.add_argument("--top", "-n", type=int, default=10, help="Top N ETS (default: 10)")
    args = ap.parse_args(argv)

    if not args.territorio and not args.prov and not args.regione:
        ap.error("Specifica un comune, --prov o --regione")

    con = duckdb.connect()
    con.execute("SET memory_limit='1GB'")

    md = vista_territorio(con, comune=args.territorio,
                          prov=args.prov, regione=args.regione,
                          top_n=args.top)

    OUT.mkdir(parents=True, exist_ok=True)
    slug = (args.territorio or args.prov or args.regione or "unknown").lower()
    slug = "".join(c if c.isalnum() or c == "-" else "_" for c in slug)
    target = OUT / f"{slug}.md"
    target.write_text(md)
    print(f"  vista scritta: {target}")

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
