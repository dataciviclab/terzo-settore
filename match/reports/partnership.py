#!/usr/bin/env python3
"""Partnership — suggerisce ETS partner per collaborazione.

Uso:
    python3 match/reports/partnership.py --cf 02006180364
    python3 match/reports/partnership.py --cf 02006180364 --top 5
"""

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))

from lib.format import fmt_euro

ETS_FILE = str(ROOT / "data/unified_ets.parquet")


def partner_report(cf, top_n=10):
    con = duckdb.connect()

    # 1. Profilo ETS target
    target = con.sql(f"""
        SELECT codice_fiscale, denominazione, comune, provincia, sezione,
               capacita_progettuale, numero_appalti, importo_appalti,
               importo_5x1000_2025, ha_finanziamenti_ue,
               subappalti, patrimonio_immobili, temi_anac
        FROM '{ETS_FILE}'
        WHERE codice_fiscale = '{cf}'
    """).fetchdf()
    if target.empty:
        print(f"❌ ETS {cf} non trovato")
        return

    t = target.iloc[0]
    provincia = t['provincia']
    temi = set(t['temi_anac'].split(',')) if t['temi_anac'] else set()

    print(f"📋 PARTNER PER: {t['denominazione']}")
    print(f"    {t['comune']} ({provincia}) — {t['sezione']} — {t['capacita_progettuale']}")
    print(f"    {int(t['numero_appalti'])} appalti | UE: {'✅' if t['ha_finanziamenti_ue'] else '❌'} | temi: {', '.join(list(temi)[:5])}")
    print()

    # 2. Partner ESISTENTI (ATI/RTI condivisi)
    partner_rti = con.sql(f"""
        SELECT DISTINCT a2.codice_fiscale as cf, r.denominazione, r.comune, r.provincia,
               r.capacita_progettuale, count(DISTINCT a1.cig) as n_cig_insieme
        FROM read_parquet('https://storage.googleapis.com/dataciviclab-clean/anac_aggiudicatari/2026/anac_aggiudicatari_2026_clean.parquet', union_by_name=true) a1
        JOIN read_parquet('https://storage.googleapis.com/dataciviclab-clean/anac_aggiudicatari/2026/anac_aggiudicatari_2026_clean.parquet', union_by_name=true) a2
          ON a1.cig = a2.cig AND a1.codice_fiscale != a2.codice_fiscale
        JOIN '{ETS_FILE}' r ON a2.codice_fiscale = r.codice_fiscale
        WHERE a1.codice_fiscale = '{cf}'
        GROUP BY a2.codice_fiscale, r.denominazione, r.comune, r.provincia, r.capacita_progettuale
        ORDER BY n_cig_insieme DESC
        LIMIT {top_n}
    """).fetchdf()

    if not partner_rti.empty:
        print(f"🔗 PARTNER ESISTENTI (ATI/RTI insieme):")
        for _, row in partner_rti.iterrows():
            print(f"    · {row['denominazione'][:50]} — {row['comune']} ({row['provincia']}) — {int(row['n_cig_insieme'])} CIG insieme")
        print()

    # 3. Partner POTENZIALI (stessa provincia, temi simili, complementari)
    partners = con.sql(f"""
        WITH target_temi AS (
            SELECT unnest(string_split(temi_anac, ',')) as tema FROM '{ETS_FILE}' WHERE codice_fiscale = '{cf}'
        )
        SELECT a.codice_fiscale, a.denominazione, a.comune, a.provincia, a.sezione,
               a.capacita_progettuale, a.numero_appalti, a.importo_5x1000_2025,
               a.ha_finanziamenti_ue, a.subappalti, a.patrimonio_immobili,
               CASE
                 WHEN a.ha_finanziamenti_ue AND NOT target.ha_finanziamenti_ue THEN '✅ ha grant UE'
                 WHEN a.ha_appalti_pubblici AND target.numero_appalti = 0 THEN '✅ ha appalti'
                 WHEN a.importo_5x1000_2025 > 5000 AND (target.importo_5x1000_2025 IS NULL OR target.importo_5x1000_2025 = 0) THEN '✅ ha 5x1000'
                 ELSE 'simile'
               END as complementarieta
        FROM '{ETS_FILE}' a
        CROSS JOIN (SELECT * FROM '{ETS_FILE}' WHERE codice_fiscale = '{cf}') target
        WHERE a.provincia = '{provincia}'
          AND a.codice_fiscale != '{cf}'
          AND a.capacita_progettuale IN ('alta', 'medio-alta')
        ORDER BY a.numero_appalti DESC
        LIMIT {top_n}
    """).fetchdf()

    if not partners.empty:
        print(f"📍 POTENZIALI (stessa provincia {provincia}):")
        for _, row in partners.iterrows():
            ue = ' UE' if row['ha_finanziamenti_ue'] else ''
            c5 = f" €{float(row['importo_5x1000_2025']):,.0f}" if row['importo_5x1000_2025'] else ''
            comp = f" — {row['complementarieta']}" if '✅' in str(row['complementarieta']) else ""
            print(f"    · {row['denominazione'][:50]} — {row['comune']}")
            print(f"      {row['capacita_progettuale']}, {int(row['numero_appalti'])} appalti{ue}{c5}{comp}")
        print()

    # 4. Subappalti: ETS che hanno subappaltato a questo ETS
    sub_in = con.sql(f"""
        SELECT DISTINCT s.codice_fiscale as cf, r.denominazione, count(*) as n
        FROM read_parquet('https://storage.googleapis.com/dataciviclab-clean/anac_subappalti/2026/anac_subappalti_2026_clean.parquet', union_by_name=true) s
        JOIN '{ETS_FILE}' r ON s.codice_fiscale = r.codice_fiscale
        WHERE s.cf_subappaltante = '{cf}'
        GROUP BY s.codice_fiscale, r.denominazione
        ORDER BY n DESC LIMIT 5
    """).fetchdf()
    if not sub_in.empty:
        print(f"🔄 SUBAPPALTI RICEVUTI (chi ha subappaltato a questo ETS):")
        for _, row in sub_in.iterrows():
            print(f"    · {row['denominazione'][:50]} — {int(row['n'])} subappalti")
        print()

    con.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Partner ETS")
    parser.add_argument("--cf", required=True, help="CF ETS")
    parser.add_argument("--top", type=int, default=10, help="Numero partner")
    args = parser.parse_args()
    partner_report(args.cf, args.top)


if __name__ == "__main__":
    main()
