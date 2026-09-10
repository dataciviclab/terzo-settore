"""Panoramica — Cosa succede nel terzo settore?"""


import altair as alt
import streamlit as st
from sources import (
    capacita_progettuale,
    fondi_per_fonte,
    kpi_con_5xmille,
    kpi_con_aiuti,
    kpi_con_appalti,
    kpi_nazionali,
    top_ets_5xmille,
)

st.title("Terzo Settore Italiano")
st.caption("Dati: RUNTS + 8 fonti (ANAC/ADE/FTS/RNA/PNRR/MEF) + OpenCoesione")

# -- KPI
tot = kpi_nazionali()
con_5xm = kpi_con_5xmille()
con_app = kpi_con_appalti()
con_aiu = kpi_con_aiuti()

col1, col2, col3, col4 = st.columns(4)
col1.metric("ETS totali", f"{tot:,}")
col2.metric("Con 5x1000", f"{con_5xm:,}")
col3.metric("Con appalti ANAC", f"{con_app:,}")
col4.metric("Con aiuti stato", f"{con_aiu:,}")

st.markdown("---")

# -- Fondi per fonte
st.subheader("Fondi per fonte")

fonti = fondi_per_fonte()
if not fonti.empty:
    chart = (
        alt.Chart(fonti[fonti["fonte"] != "Coesione"])
        .mark_bar(color="#3b82f6")
        .encode(
            y=alt.Y("fonte:N", title=None, sort="-x"),
            x=alt.X("importo:Q", title="Importo (eur)", axis=alt.Axis(format="~s")),
            tooltip=["fonte", "enti", "importo"],
        )
        .properties(height=200)
    )
    st.altair_chart(chart, width="stretch")

# -- Capacita progettuale
st.subheader(" capacita progettuale")

cap = capacita_progettuale()
if not cap.empty:
    chart = (
        alt.Chart(cap)
        .mark_bar()
        .encode(
            y=alt.Y("livello:N", title=None),
            x=alt.X("enti:Q", title="Enti"),
            color=alt.Color("livello:N", scale={
                "domain": ["sconosciuta", "base", "media", "medio-alta", "alta"],
                "range": ["#dc2626", "#f97316", "#fbbf24", "#22c55e", "#16a34a"],
            }, legend=None),
            tooltip=["livello", "enti"],
        )
        .properties(height=180)
    )
    st.altair_chart(chart, width="stretch")

st.markdown("---")

# -- Top 15 ETS per 5x1000 2025
st.subheader("Top 15 ETS per 5x1000 (2025)")

top = top_ets_5xmille()
if not top.empty:
    st.dataframe(top, column_config={
        "denominazione": "Denominazione",
        "comune": "Comune",
        "provincia": "Prov",
        "capacita_progettuale": " capacita",
        "importo_5x1000_2025": st.column_config.NumberColumn("5x1000 2025", format="eur %.0f"),
    }, hide_index=True, width="stretch")
