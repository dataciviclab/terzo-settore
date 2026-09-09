"""Territorio — Panorama del terzo settore per territorio."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import altair as alt
import streamlit as st
from sources import (
    elenco_province, elenco_regioni, territorio_riepilogo,
    territorio_fonti, territorio_top_comuni, confronto_territorio,
)

st.title("🗺️ Territorio")
st.caption("Il terzo settore italiano per comune, provincia e regione")

# -- Selezione territorio
col1, col2 = st.columns(2)

with col1:
    regioni = elenco_regioni()
    regione = st.selectbox("Regione", ["Tutte"] + regioni["regione"].tolist(), key="terr_reg")

with col2:
    province = elenco_province()
    provincia = st.selectbox("Provincia", ["Tutte"] + province["provincia"].tolist(), key="terr_prov")

# Filtri
prov = provincia if provincia != "Tutte" else None
reg = regione if regione != "Tutte" else None

# -- Riepilogo
st.markdown("---")
st.subheader("📊 Riepilogo")

riepilogo = territorio_riepilogo(prov, reg)
if not riepilogo.empty:
    r = riepilogo.iloc[0]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📋 ETS totali", f"{int(r['ets_totali']):,}")
    col2.metric("🎯 Capacità alta/media-alta", f"{int(r['capacita_media_alta']):,}")
    col3.metric("💰 Con 5×1000", f"{int(r['con_5xmille']):,}")
    col4.metric("🏛️ Con coesione", f"{int(r.get('con_anac', 0)):,}")
    
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("ODV", f"{int(r['odv']):,}")
    col6.metric("APS", f"{int(r['aps']):,}")
    col7.metric("Imprese Sociali", f"{int(r['imprese_sociali']):,}")
    col8.metric("Media 5×1000", f"€{int(r.get('media_5xmille', 0)):,}")

st.markdown("---")

# -- Confronto con nazionale (solo per provincia)
if prov:
    st.subheader("📈 Confronto con nazionale")
    confronto = confronto_territorio(prov)
    if not confronto.empty:
        st.dataframe(confronto, column_config={
            "totale": st.column_config.NumberColumn("ETS totali", format="%d"),
            "attivi": st.column_config.NumberColumn("Capacità alta", format="%d"),
            "con_5xmille": st.column_config.NumberColumn("Con 5×1000", format="%d"),
            "con_anac": st.column_config.NumberColumn("Con ANAC", format="%d"),
        }, hide_index=True, width="stretch")

# -- Fonti per territorio
st.markdown("---")
st.subheader("💰 Fonti per territorio")

fonti = territorio_fonti(prov, reg)
if not fonti.empty:
    chart = (
        alt.Chart(fonti)
        .mark_bar(color="#3b82f6")
        .encode(
            y=alt.Y("fonte:N", title=None, sort="-x"),
            x=alt.X("enti:Q", title="Enti"),
            tooltip=["fonte", "enti"],
        )
        .properties(height=200)
    )
    st.altair_chart(chart, width="stretch")

# -- Top comuni
st.markdown("---")
st.subheader("🏘️ Top comuni per ETS")

top_comuni = territorio_top_comuni(prov, reg)
if not top_comuni.empty:
    st.dataframe(top_comuni, column_config={
        "comune": "Comune",
        "provincia": "Prov",
        "ets_tot": st.column_config.NumberColumn("ETS totali", format="%d"),
        "con_5xmille": st.column_config.NumberColumn("Con 5×1000", format="%d"),
        "con_anac": st.column_config.NumberColumn("Con ANAC", format="%d"),
        "attivi": st.column_config.NumberColumn("Capacità alta", format="%d"),
    }, hide_index=True, width="stretch")
