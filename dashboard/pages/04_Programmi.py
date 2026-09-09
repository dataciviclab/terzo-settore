"""Programmi — Quali programmi finanziano gli ETS?"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import altair as alt
import streamlit as st
from sources import fts_per_programma, pnrr_per_programma

st.title("🇪🇺 Programmi")
st.caption("Quali programmi PNRR e UE finanziano gli ETS italiani?")

# -- PNRR
st.subheader("🇮🇹 PNRR — Per missione")

pnrr = pnrr_per_programma()
if pnrr.empty:
    st.info("Nessun dato PNRR disponibile.")
else:
    chart = (
        alt.Chart(pnrr)
        .mark_bar(color="#dc2626")
        .encode(
            y=alt.Y("descrizione_missione:N", title=None, sort="-x"),
            x=alt.X("fin_totale:Q", title="Finanziamento totale (€)", axis=alt.Axis(format="~s")),
            tooltip=["descrizione_missione", "n_ets", "fin_totale"],
        )
        .properties(height=300)
    )
    st.altair_chart(chart, width="stretch")

    st.dataframe(pnrr, column_config={
        "programma": "Programma",
        "missione": "Missione",
        "descrizione_missione": "Descrizione",
        "n_ets": st.column_config.NumberColumn("ETS", format="%d"),
        "fin_totale": st.column_config.NumberColumn("Finanziamento", format="€%.0f"),
    }, hide_index=True, width="stretch")

st.markdown("---")

# -- Grant UE
st.subheader("🇪🇺 Grant UE — Per programma")

fts = fts_per_programma()
if fts.empty:
    st.info("Nessun dato Grant UE disponibile.")
else:
    chart = (
        alt.Chart(fts)
        .mark_bar(color="#2563eb")
        .encode(
            y=alt.Y("programma_ue:N", title=None, sort="-x"),
            x=alt.X("importo_totale:Q", title="Importo totale (€)", axis=alt.Axis(format="~s")),
            tooltip=["programma_ue", "n_ets", "n_grant", "importo_totale"],
        )
        .properties(height=300)
    )
    st.altair_chart(chart, width="stretch")

    st.dataframe(fts, column_config={
        "programma_ue": "Programma",
        "n_ets": st.column_config.NumberColumn("ETS", format="%d"),
        "n_grant": st.column_config.NumberColumn("Grant", format="%d"),
        "importo_totale": st.column_config.NumberColumn("Importo", format="€%.0f"),
    }, hide_index=True, width="stretch")
