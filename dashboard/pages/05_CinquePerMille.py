"""5x1000 — Che tipo di ETS ricevono il 5 per mille?"""

import sys

import altair as alt
import pandas as pd
import streamlit as st
from sources import cinque_per_anno, cinque_per_tipologia, top_ets_5x1000

st.title("💰 5×1000")
st.caption("Distribuzione del 5 per mille tra gli ETS italiani")

# -- Trend temporale
st.subheader("📈 Trend 5×1000 per anno")

trend = cinque_per_anno()
if not trend.empty:
    col1, col2, col3 = st.columns(3)
    col1.metric("Anni disponibili", f"{len(trend)}")
    col2.metric("ETS totali (2025)", f"{int(trend[trend['anno']==2025]['n_ets'].sum()):,}" if 2025 in trend['anno'].values else "-")
    col3.metric("Importo totale (2025)",
                f"€{trend[trend['anno']==2025]['importo_totale'].sum()/1e6:,.0f}M" if 2025 in trend['anno'].values else "-")

    chart = (
        alt.Chart(trend)
        .mark_line(color="#3b82f6", point=True, strokeWidth=2)
        .encode(
            x=alt.X("anno:O", title="Anno"),
            y=alt.Y("n_ets:Q", title="Numero ETS"),
            tooltip=["anno", "n_ets", "importo_totale", "importo_medio"],
        )
        .properties(height=250)
    )
    st.altair_chart(chart, width="stretch")

    st.dataframe(trend, column_config={
        "anno": "Anno",
        "n_ets": st.column_config.NumberColumn("ETS", format="%d"),
        "importo_totale": st.column_config.NumberColumn("Importo totale", format="€%.0f"),
        "importo_medio": st.column_config.NumberColumn("Importo medio", format="€%.0f"),
    }, hide_index=True, width="stretch")

st.markdown("---")

# -- Distribuzione per tipologia (flag tematici)
st.subheader("🎯 Distribuzione per tipologia di attivita'")

tipo = cinque_per_tipologia()
if not tipo.empty:
    r = tipo.iloc[0]
    data = pd.DataFrame({
        "Tipologia": ["ASD (sport)", "Ricerca scientifica", "Ricerca sanitaria",
                       "Beni culturali", "Area protetta", "Comuni"],
        "ETS": [int(r.get("asd", 0)), int(r.get("ricerca_scientifica", 0)),
                 int(r.get("ricerca_sanitaria", 0)), int(r.get("beni_culturali", 0)),
                 int(r.get("area_protetta", 0)), int(r.get("comuni", 0))],
    })
    data = data[data["ETS"] > 0].sort_values("ETS", ascending=False)

    chart = (
        alt.Chart(data)
        .mark_bar()
        .encode(
            y=alt.Y("Tipologia:N", title=None, sort="-x"),
            x=alt.X("ETS:Q", title="Numero ETS"),
            color=alt.Color("Tipologia:N", legend=None, scale=alt.Scale(scheme="category10")),
            tooltip=["Tipologia", "ETS"],
        )
        .properties(height=250)
    )
    st.altair_chart(chart, width="stretch")

    tot = int(r.get("totale", 0))
    st.metric("ETS totali con 5×1000", f"{tot:,}")

st.markdown("---")

# -- Top ETS
st.subheader("🏆 Top 20 ETS per importo 5×1000")

top = top_ets_5x1000()
if not top.empty:
    st.dataframe(top, column_config={
        "cf": "CF",
        "denominazione": "Denominazione",
        "comune": "Comune",
        "provincia": "Prov",
        "importo_totale": st.column_config.NumberColumn("Importo totale", format="€%.0f"),
        "anni": st.column_config.NumberColumn("Anni", format="%d"),
        "flag_asd": st.column_config.CheckboxColumn("ASD"),
        "flag_ricerca_scientifica": st.column_config.CheckboxColumn("Ricerca"),
    }, hide_index=True, width="stretch")
