"""Anagrafe — Chi sono gli ETS nel mio territorio?"""

import streamlit as st
from sources import anagrafe_join, elenco_sezioni

st.title("Anagrafe ETS")

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

df = anagrafe_join(
    comune=comune or None,
    prov=prov or None,
    sezione=sezione if sezione != "Tutte" else None,
    search=search or None,
)

st.write(f"**{len(df)} enti** trovati")

if not df.empty:
    st.dataframe(df, column_config={
        "codice_fiscale": "CF",
        "denominazione": "Denominazione",
        "sezione": "Sezione",
        "comune": "Comune",
        "provincia": "Prov",
        "data_iscrizione": "Iscrizione",
        "capacita_progettuale": st.column_config.TextColumn("Capacita"),
    }, hide_index=True, width="stretch", height=min(35*len(df)+35, 600))
