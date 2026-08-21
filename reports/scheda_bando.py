#!/usr/bin/env python3
"""Scheda Bando: profilo completo di un bando con ETS compatibili.

Uso:
    python3 reports/scheda_bando.py                    # lista bandi disponibili
    python3 reports/scheda_bando.py 5                  # scheda bando #5
    python3 reports/scheda_bando.py --search "sport"   # cerca per keyword
    python3 reports/scheda_bando.py --top 15 3         # bando #3, top 15 ETS
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]

from match.pipeline import load_bandi, normalise_bando
from match.funnel import match_bando_funnel, gate_territorio, gate_sezione
from lib.temi import tema_principale, normalizza_tags, sezioni_per_tag
from lib.config import ETS_FILE, BANDI_FILES

OUT = ROOT / "data" / "reporting" / "schede_bandi"


def fmt_euro(v) -> str:
    if v is None or v == 0:
        return "-"
    if isinstance(v, float) and v == int(v):
        return f"\u20ac{int(v):,}".replace(",", ".")
    return f"\u20ac{v:,.0f}"


def fmt_int(v) -> str:
    if v is None or v == 0:
        return "0"
    return f"{int(v):,}".replace(",", ".")


# -- Listing ---------------------------------------------------------------


def lista_bandi():
    bandi = load_bandi()
    if not bandi:
        print("Nessun bando trovato in", [str(f) for f in BANDI_FILES])
        return
    print(f"\n{'#':>3}  {'Scadenza':10}  {'Budget':>12}  {'Tags':30}  Titolo")
    print(f"{'\u2500'*3}  {'\u2500'*10}  {'\u2500'*12}  {'\u2500'*30}  {'\u2500'*40}")
    for i, b in enumerate(bandi):
        tags = b.get("tag", [])
        tags_str = ", ".join(tags[:3])
        if len(tags) > 3:
            tags_str += f" +{len(tags)-3}"
        scad = str(b.get("scadenza") or "-")
        if len(scad) > 10:
            scad = scad[:10]
        budget = fmt_euro(b.get("budget"))
        titolo = (b.get("titolo") or "-")[:55]
        print(f"{i:>3}  {scad:10}  {budget:>12}  {tags_str:30}  {titolo}")
    print(f"\n{len(bandi)} bandi totali. Usa: python3 reports/scheda_bando.py <numero>")


def cerca_bandi(query: str) -> list[int]:
    bandi = load_bandi()
    q = query.lower()
    return [i for i, b in enumerate(bandi)
            if q in " ".join(str(b.get(k, "") or "") for k in
                            ("titolo", "ente_erogatore", "tag", "categorie")).lower()]


# -- Stats territoriali ----------------------------------------------------


def _stats_territoriali(con, tags, territorio) -> dict | None:
    gate_terr = gate_territorio(territorio)
    gate_sez = gate_sezione(tags)
    sql = f"""
    SELECT count(*) as totale,
           count(CASE WHEN capacita_progettuale IN ('alta', 'medio-alta') THEN 1 END) as attivi,
           ROUND(avg(CASE WHEN importo_5x1000_2025 > 0 THEN importo_5x1000_2025 END), 0) as media_5x
    FROM '{ETS_FILE}' WHERE 1=1 {gate_sez} {gate_terr}
    """
    try:
        row = con.execute(sql).fetchone()
        if row and row[0] > 0:
            t = row[0]
            a = row[1]
            return {"totale": t, "attivi": a,
                    "pct_attivi": round(a * 100 / t, 1) if t else 0,
                    "media_5x1000": row[2] or 0}
    except Exception:
        pass
    return None


# -- Generazione scheda ----------------------------------------------------


def scheda_bando(con: duckdb.DuckDBPyConnection, b: dict, top_n: int = 10) -> str:
    titolo, url, scadenza_str, ente, tags, territorio, fonte = normalise_bando(b)

    tema_prim = tema_principale(tags)
    normalizzati = normalizza_tags(tags)
    sez_gate = sezioni_per_tag([tema_prim]) if tema_prim else []

    testo_bando = " ".join(str(b.get(k, "") or "") for k in
                           ("titolo", "descrizione", "obiettivi", "ammissibili", "testo_nlp"))
    df_top = match_bando_funnel(con, tags, limit=top_n, territorio=territorio, testo=testo_bando)

    n_idonei = len(df_top)
    try:
        df_all = match_bando_funnel(con, tags, limit=10_000_000, territorio=territorio, testo=testo_bando)
        n_idonei = len(df_all)
    except Exception:
        pass

    stats = _stats_territoriali(con, tags, territorio)

    md = [f"# \U0001f4cb {titolo}", ""]

    md += ["## Anagrafica", "", "| Dato | Valore |", "|---|---|"]
    md += [f"| Ente erogatore | {ente or '-'} |"]
    md += [f"| Scadenza | {scadenza_str or '-'} |"]
    md += [f"| Budget | {fmt_euro(b.get('budget'))} |"]
    md += [f"| Fonte | {fonte} |"]
    if url:
        md += [f"| Link | [{url[:60]}...]({url}) |"]

    md += ["", "## Temi", ""]
    if tema_prim:
        md += [f"**Principale**: {tema_prim}"]
    altri = [t for t in normalizzati if t != tema_prim]
    if altri:
        md += [f"**Secondari**: {', '.join(altri)}"]
    if sez_gate:
        md += [f"**Sezioni ammesse**: {', '.join(sez_gate)}"]

    md += ["", "## Territorio", ""]
    if territorio and territorio != ["Nazionale/da verificare"]:
        md += [f"Area: {', '.join(territorio)}"]
    else:
        md += ["Area: Nazionale"]

    n_show = min(top_n, len(df_top))
    md += ["", f"## ETS compatibili \u2014 Top {n_show} su {n_idonei} idonei", ""]
    if df_top.empty:
        md += ["Nessun ETS compatibile trovato."]
    else:
        md += ["| # | ETS | Comune | Sezione | Capacit\u00e0 | Score | Motivo |",
               "|---|---|---|---|---|---|---|"]
        for i, row in df_top.iterrows():
            nome = (row.get("denominazione") or "-")[:45]
            comune = row.get("comune", "-")
            sez = (row.get("sezione") or "-")[:25]
            cap = row.get("capacita_progettuale", "-")
            score = row.get("score", 0)
            motivo = (row.get("motivo_match") or "-").replace("_", " ")
            md += [f"| {i+1} | {nome} | {comune} | {sez} | {cap} | {score} | {motivo} |"]

    if stats:
        md += ["", "## Statistiche territoriali", ""]
        md += [f"- ETS totali nel territorio: **{fmt_int(stats['totale'])}**"]
        md += [f"- Con capacit\u00e0 medio-alta+: **{fmt_int(stats['attivi'])}** ({stats['pct_attivi']}%)"]
        if stats.get("media_5x1000", 0) > 0:
            md += [f"- 5x1000 medio: **{fmt_euro(stats['media_5x1000'])}**"]

    md += ["", "---", "",
           f"_Dati: mart ETS ({fmt_int(n_idonei)} idonei) + bandi {fonte}. "
           f"Generata da `reports/scheda_bando.py`._"]

    return "\n".join(md)


# -- CLI -------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Scheda Bando \u2014 profilo bando + ETS compatibili")
    ap.add_argument("index", nargs="?", type=int, help="Indice del bando nella lista")
    ap.add_argument("--search", "-s", help="Cerca bandi per keyword")
    ap.add_argument("--top", "-n", type=int, default=10, help="Numero top ETS (default: 10)")
    ap.add_argument("--list", "-l", action="store_true", help="Mostra lista bandi")
    args = ap.parse_args(argv)

    if args.list or (args.index is None and not args.search):
        lista_bandi()
        return 0

    bandi = load_bandi()
    if not bandi:
        print("Nessun bando trovato")
        return 1

    if args.search:
        indici = cerca_bandi(args.search)
        if not indici:
            print(f"Nessun bando trovato per '{args.search}'")
            return 1
        print(f"Trovati {len(indici)} bandi per '{args.search}':")
        for i in indici:
            b = bandi[i]
            print(f"  [{i}] {(b.get('titolo') or '-')[:70]}")
        if len(indici) == 1:
            args.index = indici[0]
        else:
            return 0

    if args.index is None or args.index >= len(bandi):
        print(f"Indice {args.index} fuori range (0-{len(bandi)-1})")
        return 1

    b = bandi[args.index]
    con = duckdb.connect()
    con.execute("SET memory_limit='1GB'")

    md = scheda_bando(con, b, top_n=args.top)

    OUT.mkdir(parents=True, exist_ok=True)
    slug = (b.get("titolo") or f"bando_{args.index}")[:40]
    slug = "".join(c if c.isalnum() or c in "-_ " else "" for c in slug).strip().replace(" ", "_")
    target = OUT / f"{args.index:03d}_{slug}.md"
    target.write_text(md)
    print(f"  scheda scritta: {target}")

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
