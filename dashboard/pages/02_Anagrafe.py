"""Anagrafe — Chi sono gli ETS nel mio territorio?"""

import sys

import streamlit as st
from lab_connectors.duckdb import safe_connect
from sources import MART_ETS, RUNTS, elenco_sezioni

st.title("📋 Anagrafe ETS")

sezioni = elenco_sezioni()
sez_opts = ["Tutte"] + sezioni["sezione"].dropna().tolist()

c1, c2, c3 = st.columns(3)
with c1:
    prov = st.text_input("Provincia", placeholder="BO", key="anag_prov")
with c2:
    comune = st.text_input("Comune", placeholder="Bologna", key="anag_com")
with c3:
    sezione = st.selectbox("Sezione", sez_opts, key="anag_sez")

search = st.text_input("Cerca per nome o CF", key="anag_search")

# Join RUNTS + mart per avere anche la capacita'
where = []
if comune:
    where.append(f"lower(r.comune) = '{comune.lower().replace(chr(39),'')}'")
if prov:
    where.append(f"upper(r.provincia) = '{prov.upper()}'")
if sezione and sezione != "Tutte":
    where.append(f"r.sezione = '{sezione}'")
if search:
    s = search.replace("'", "''")
    where.append(f"(r.denominazione LIKE '%{s}%' OR r.codice_fiscale LIKE '%{s}%')")
w = " WHERE " + " AND ".join(where) if where else ""

with safe_connect() as con:
    df = con.sql(f"""
        SELECT r.codice_fiscale, r.denominazione, r.sezione, r.comune, r.provincia,
               r.data_iscrizione, m.capacita_progettuale
        FROM read_parquet('{RUNTS}') r
        LEFT JOIN read_parquet('{MART_ETS}') m ON r.codice_fiscale = m.codice_fiscale
        {w}
        ORDER BY r.denominazione
        LIMIT 500
    """).df()

st.write(f"**{len(df)} enti** trovati")

if not df.empty:
    st.dataframe(df, column_config={
        "codice_fiscale": "CF",
        "denominazione": "Denominazione",
        "sezione": "Sezione",
        "comune": "Comune",
        "provincia": "Prov",
        "data_iscrizione": "Iscrizione",
        "capacita_progettuale": st.column_config.TextColumn("Capacità"),
    }, hide_index=True, width="stretch", height=min(35*len(df)+35, 600))
