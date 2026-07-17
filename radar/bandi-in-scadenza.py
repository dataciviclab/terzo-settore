#!/usr/bin/env python3
"""Vista latest del radar: bandi operativi in scadenza nei prossimi 60 giorni."""

import json, sys
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))

from radar.core import fmt_euro, fmt_match_reason, fmt_tags, fmt_text
from patterns import normalize_comune

ETS_FILE = ROOT / "data" / "unified_ets.parquet"
RADAR_JSON = ROOT / "cruscotto" / "radar-completo.json"
GCS_BASE = "https://storage.googleapis.com/dataciviclab-clean"
INPS_RDC_URL = f"{GCS_BASE}/inps_rdc_pdc/2020/inps_rdc_pdc_2020_clean.parquet"
COMUNI_URL = f"{GCS_BASE}/istat_elenco_comuni/2026/istat_elenco_comuni_2026_clean.parquet"
UNIFIED_COMUNI_URL = f"{GCS_BASE}/unified_comuni/2026/unified_comuni_2026_clean.parquet"
_COMUNI_LOOKUP = None  # cache per _build_comune_lookup

ANAC_URLS = ", ".join(
    f"'{GCS_BASE}/anac_bandi_gara/{y}/anac_bandi_gara_{y}_clean.parquet'"
    for y in [2023, 2024, 2025]
)


def load_scan():
    """Carica scan da JSON già calcolato."""
    if not RADAR_JSON.exists():
        print(f"❌ {RADAR_JSON} non trovato. Esegui prima scan_completo.py")
        sys.exit(1)
    with open(RADAR_JSON) as f:
        return json.load(f)


# Cache per comuni_ets (caricato una tantum)
_COMUNI_ETS = None
_COMUNI_ETS_PATH = ROOT / "data" / "comuni_ets.parquet"


def _get_comuni_ets(con):
    """Carica comuni_ets.parquet (lo costruisce se non esiste)."""
    global _COMUNI_ETS
    if _COMUNI_ETS is not None:
        return _COMUNI_ETS
    if not _COMUNI_ETS_PATH.exists():
        print("⚠️  comuni_ets.parquet non trovato. Eseguo build...")
        import subprocess
        subprocess.run([sys.executable, str(ROOT / "sql/build_comuni_ets.py")], check=True)
    _COMUNI_ETS = con.sql(f"SELECT * FROM '{_COMUNI_ETS_PATH}'").fetchdf()
    return _COMUNI_ETS


def gap_territoriale(con):
    """Gap analysis: legge da comuni_ets.parquet (pre-aggregato).
    
    Mostra comuni con appalti riservati ANAC o gap sociale,
    ordinati per appalti decrescenti, ETS ok ascendenti.
    """
    df = _get_comuni_ets(con)
    
    rows = []
    for _, r in df.iterrows():
        appalti = int(r["appalti_riservati"]) if pd.notna(r.get("appalti_riservati")) else 0
        ets_ok = int(r["ets_matchabili"]) if pd.notna(r.get("ets_matchabili")) else 0
        rd_pct = float(r["rd_pct"]) if pd.notna(r.get("rd_pct")) else 0.0
        pop = int(r["popolazione"]) if pd.notna(r.get("popolazione")) else 0
        reddito = int(r["reddito_procapite"]) if pd.notna(r.get("reddito_procapite")) else 0
        importo = float(r["importo_anac_totale"]) if pd.notna(r.get("importo_anac_totale")) else 0
        ets_tot = int(r["ets_tot"]) if pd.notna(r.get("ets_tot")) else 0
        nuclei = int(r["nuclei_rdc"]) if pd.notna(r.get("nuclei_rdc")) else 0
        
        if appalti == 0 and rd_pct <= 5:
            continue
        
        if appalti >= 5 and ets_ok < 5:
            segnale = "🔴 domanda pubblica alta, pochi ETS"
        elif appalti >= 1 and ets_ok == 0:
            segnale = "🟠 domanda pubblica, zero ETS"
        elif ets_ok == 0 and rd_pct > 10:
            segnale = "🟡 RdC alto, zero ETS"
        else:
            segnale = ""
        
        rows.append({
            "denominazione": str(r["comune"]),
            "sigla_provincia": str(r["provincia"]) if pd.notna(r.get("provincia")) else "",
            "pop": pop, "reddito": reddito,
            "appalti": appalti, "importo_M": round(importo / 1_000_000, 1),
            "ets_ok": ets_ok, "ets_tot": ets_tot,
            "rd_pct": rd_pct, "nuclei_rdc": nuclei,
            "gap_segnale": segnale,
        })
    
    if not rows:
        return []
    
    df_out = pd.DataFrame(rows)
    df_out = df_out.sort_values(["appalti", "ets_ok"], ascending=[False, True]).head(10)
    return df_out.to_dict("records")


def territory_matches(r, filtro_territorio):
    if not filtro_territorio:
        return True
    needle = filtro_territorio.lower()
    territory = " ".join(r.get("territorio", [])).lower()
    candidates = " ".join(
        f"{fmt_text(c.get('comune'), '')} {fmt_text(c.get('provincia'), '')}".lower()
        for c in r.get("candidati", [])
    )
    return needle in territory or needle in candidates


def genera_report(scan, con, filtro_territorio=None, giorni=60):
    oggi = datetime.now()
    risultati = []
    for r in scan["resultados"]:
        gg = r.get("gg_rimasti", r.get("gg", 999))
        if 0 <= gg <= giorni and territory_matches(r, filtro_territorio):
            r["gg"] = gg  # normalizza
            risultati.append(r)

    lines = []
    lines.append(f"# 📡 Radar bandi — {oggi.strftime('%d/%m/%Y')}")
    lines.append("")
    lines.append(f"Bandi operativi in scadenza nei prossimi {giorni}gg: **{len(risultati)}**")
    if filtro_territorio:
        lines.append(f"Filtro territorio: **{filtro_territorio}**")
    lines.append("")

    for r in sorted(risultati, key=lambda x: x["gg"]):
        lines.append(f"## {r['titolo'][:80]}")
        lines.append(f"- **Ente**: {r['ente'] or '?'}")
        lines.append(f"- **Scadenza**: {r['scadenza']} ({r['gg']} giorni)")
        lines.append(f"- **Stato**: {r['status']}")
        lines.append(f"- **Territorio**: {', '.join(r['territorio'])}")
        lines.append(f"- **Tag**: {fmt_tags(r['tags'])}")
        lines.append("")
        for c in r["candidati"][:5]:
            comune = fmt_text(c.get("comune"), "")
            provincia = fmt_text(c.get("provincia"))
        cap = c.get("capacita", c.get("capacita_progettuale", "?"))
        lines.append(
            f"  · **{cap}** {c['denominazione'][:55]} "
            f"— {comune} ({provincia}) — score {int(c.get('score', 0))}, "
            f"{fmt_match_reason(c)} — 5x1000: {fmt_euro(c.get('cinque_2025'))}"
        )
        lines.append("")

    lines.append("---")
    lines.append("## ⚠️ Gap territoriali (appalti riservati ANAC + ETS + RdC)")
    lines.append("")
    lines.append("| Comune | Prov | Appalti riservati | ETS ok | RdC% | Reddito | Segnale |")
    lines.append("|--------|------|------------------|--------|------|---------|---------|")
    for g in gap_territoriale(con):
        segnale = g.get("gap_segnale", "") or ""
        lines.append(
            f"| {g['denominazione'][:20]} | {g['sigla_provincia']} "
            f"| {g['appalti']} app. €{g['importo_M']}M "
            f"| {g['ets_ok']} | {g['rd_pct']}% "
            f"| €{g['reddito']:,} | {segnale} |"
        )
    lines.append("")
    lines.append(f"_Vista latest da scan condiviso: {len(scan['resultados'])} bandi operativi matchati. "
                 f"Dati ANAC: appalti riservati (L.381/1991, D.Lgs 117/2017) 2023-2025._")
    return "\n".join(lines)


def main():
    filtro = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--territorio" else None
    con = duckdb.connect()
    scan = load_scan()
    report = genera_report(scan, con, filtro_territorio=filtro)
    out = ROOT / "cruscotto" / "radar-latest.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(f"✅ Radar salvato: {out}")
    print(report[:2000])


if __name__ == "__main__":
    main()
