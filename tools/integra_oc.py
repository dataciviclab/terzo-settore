#!/usr/bin/env python3
"""Integra i dati Open Cooperazione in unified_ets.

Carica il CSV, matcha per nome+città, produce un report di arricchimento.
"""

import csv, re, sys, json
from pathlib import Path
import duckdb
import pandas as pd

OC_CSV = "data/open_cooperazione_organizzazioni.csv"
OC_PARQUET = "data/oc_organizzazioni.parquet"
ETS_FILE = "data/unified_ets.parquet"

def parse_num(val):
    if not val or not val.strip():
        return 0
    val = val.strip().replace(',', '.')
    try:
        return int(float(val))
    except:
        return 0

def parse_float(val):
    if not val or not val.strip():
        return None
    val = val.strip().replace(',', '.').replace(' ', '')
    try:
        return float(val)
    except:
        return None

def main():
    print("📥 Caricamento Open Cooperazione CSV...")
    oc_data = []
    with open(OC_CSV, encoding='latin-1') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            oc_data.append(row)

    rows = []
    for row in oc_data:
        nome = row.get('Nome organizzazione', '').strip()
        citta = row.get('Città', '').strip()
        if not nome or not citta:
            continue
        
        nome_up = nome.upper().strip()
        citta_up = citta.upper().strip()
        # Normalizza: togli ETS/APS/ODV/ASD dalla fine
        nome_norm = re.sub(r'\s+(ETS|APS|ODV|ASD|A\.P\.S\.|O\.D\.V\.|R\.L\.)$', '', nome_up)
        nome_norm = re.sub(r'[^A-Z0-9 À-ÖØ-öø-ÿ]', '', nome_norm)
        nome_norm = re.sub(r'\s+', ' ', nome_norm).strip()

        # Dipendenti totali
        dip = (
            parse_num(row.get('Dipendenti Indeterminati Maschi Italia', '0')) +
            parse_num(row.get('Dipendenti Indeterminati Femmine Italia', '0')) +
            parse_num(row.get('Dipendenti Determinati Maschi Italia', '0')) +
            parse_num(row.get('Dipendenti Determinati Femmine Italia', '0'))
        )

        rows.append({
            'nome_oc': nome_up,
            'nome_norm': nome_norm,
            'citta_oc': citta_up,
            'ets_flag': row.get('ETS DLGS 117-2017', '').strip(),
            'aics_flag': row.get('Iscritto elenco AICS', '').strip(),
            'email': row.get('Email organizzazione', '').strip(),
            'sito': row.get('Sitoweb', '').strip(),
            'telefono': row.get('Telefono', '').strip(),
            'bilancio_entrate': parse_float(row.get('Bilancio tot. Entrate', '0')),
            'bilancio_uscite': parse_float(row.get('Bilancio tot. Uscite', '0')),
            'oneri_missione': row.get('Oneri missione', '').strip(),
            'progetti': parse_num(row.get('Numero di progetti sostenuti direttamente', '0')),
            'volontari': parse_num(row.get('Numero Volontari Totale Attivi', '0')),
            'dipendenti': dip,
            'donatori_istituzionali': parse_float(row.get('Fondi donatori istituzionali', '0')),
            'fondi_5x1000': parse_float(row.get('Fondi 5x1000', '0')),
            'forma_giuridica': row.get('Forma giuritica', '').strip(),
            'totale_associati': parse_num(row.get('Numero associati', '0')),
            'sdgs': row.get('Obiettivi Sviluppo Sostenibile SDGs', '').strip()[:200],
        })

    df_oc = pd.DataFrame(rows)
    df_oc.to_parquet(OC_PARQUET, index=False)
    print(f"✅ Salvate {len(df_oc)} organizzazioni in {OC_PARQUET}")

    # Match con unified_ets
    print("\n🔗 Matching con unified_ets...")
    con = duckdb.connect()

    # Match per città + nome LIKE
    matched = con.sql(f"""
        SELECT DISTINCT e.codice_fiscale, e.denominazione, e.comune, e.provincia,
               e.capacita_progettuale,
               o.nome_oc, o.email, o.sito, o.telefono,
               o.bilancio_entrate, o.bilancio_uscite, o.oneri_missione,
               o.progetti, o.volontari, o.dipendenti,
               o.donatori_istituzionali, o.fondi_5x1000,
               o.ets_flag, o.aics_flag, o.forma_giuridica,
               o.totale_associati, o.sdgs
        FROM '{ETS_FILE}' e
        JOIN '{OC_PARQUET}' o
          ON upper(e.comune) = o.citta_oc
          AND (
              replace(upper(e.denominazione), '''', '') LIKE '%' || replace(o.nome_norm, '''', '') || '%'
              OR replace(o.nome_norm, '''', '') LIKE '%' || replace(upper(e.denominazione), '''', '') || '%'
          )
    """).fetchdf()

    print(f"\n📊 Match trovati: {len(matched)} organizzazioni")

    if matched.empty:
        print("❌ Nessun match trovato — verificare i dati")
        con.close()
        return

    # Stats
    sconosciute = matched[matched['capacita_progettuale'] == 'sconosciuta']
    con_capacita = matched[matched['capacita_progettuale'] != 'sconosciuta']
    print(f"  ETS 'sconosciuta' → matchati con OC: {len(sconosciute)}")
    print(f"  ETS già matchabili: {len(con_capacita)}")

    if not sconosciute.empty:
        print(f"\n  Esempi di 'sconosciuta' che ora hanno dati OC:")
        for _, r in sconosciute.head(10).iterrows():
            print(f"    · {r['denominazione'][:45]} ({r['comune']}) — entrate €{r['bilancio_entrate']:,.0f}" if r['bilancio_entrate'] and r['bilancio_entrate'] > 0 else f"    · {r['denominazione'][:45]} ({r['comune']})")

    # Stats capacità prima/dopo
    print(f"\n  Capacità originaria dei matchati:")
    for cap, cnt in matched['capacita_progettuale'].value_counts().items():
        print(f"    {cap}: {cnt}")

    # Nuova capacità se usassimo OC
    def new_capacity(row):
        if row['bilancio_entrate'] and row['bilancio_entrate'] > 0:
            if row['bilancio_entrate'] > 100000:
                return 'media'
            else:
                return 'base'
        if row['progetti'] and row['progetti'] >= 3:
            return 'media'
        if row['dipendenti'] and row['dipendenti'] >= 3:
            return 'media'
        return None  # keep existing

    matched['nuova_capacita'] = matched.apply(new_capacity, axis=1)
    upgrades = matched[(matched['capacita_progettuale'] == 'sconosciuta') & matched['nuova_capacita'].notna()]
    print(f"\n  📈 'Sconosciuta' che PROMUOVEREMMO con dati OC: {len(upgrades)}")
    if len(upgrades) > 0:
        for _, r in upgrades.head(5).iterrows():
            print(f"    {r['denominazione'][:45]} → {r['nuova_capacita']} (entrate €{r['bilancio_entrate']:,.0f})")

    con.close()

    # Salva report
    out = Path("cruscotto/integrazione-oc.md")
    lines = [
        "# 🔗 Integrazione Open Cooperazione",
        f"Match: {len(matched)} organizzazioni",
        f"ETS 'sconosciuta' con dati OC: {len(sconosciute)}",
        f"Promuovibili: {len(upgrades)}" if len(upgrades) > 0 else "",
        "",
        "## Top match per bilancio",
    ]
    for _, r in matched.sort_values('bilancio_entrate', ascending=False).head(20).iterrows():
        entrate = f"€{r['bilancio_entrate']:,.0f}" if r['bilancio_entrate'] and r['bilancio_entrate'] > 0 else "-"
        lines.append(f"- {r['denominazione'][:50]} — {r['comune']} — bilancio {entrate} — cap. {r['capacita_progettuale']}")
    out.write_text("\n".join(lines))
    print(f"\n✅ Report: {out}")

if __name__ == "__main__":
    main()
