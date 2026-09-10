"""Trasparenza — Chi finanzia e compra dal terzo settore?"""

import sys

import altair as alt
import streamlit as st
from sources import (
    rna_per_procedimento,
    top_soggetti_concedenti,
    top_stazioni_appaltanti,
)

st.title("🔍 Trasparenza")
st.caption("Chi finanzia e compra dal terzo settore italiano?")

# -- Soggetti concedenti (RNA)
st.subheader("🏛️ Top soggetti concedenti — Aiuti di Stato")
st.caption("Quali ministeri/enti danno piu' fondi agli ETS?")

df = top_soggetti_concedenti(20)
if df.empty:
    st.info("Nessun dato disponibile.")
else:
    chart = (
        alt.Chart(df)
        .mark_bar(color="#3b82f6")
        .encode(
            y=alt.Y("soggetto_concedente:N", title=None, sort="-x"),
            x=alt.X("importo_totale:Q", title="Importo totale (€)", axis=alt.Axis(format="~s")),
            tooltip=["soggetto_concedente", "n_beneficiari", "importo_totale"],
        )
        .properties(height=400)
    )
    st.altair_chart(chart, width="stretch")

    st.dataframe(df, column_config={
        "soggetto_concedente": "Soggetto concedente",
        "n_beneficiari": st.column_config.NumberColumn("Beneficiari", format="%d"),
        "n_concessioni": st.column_config.NumberColumn("Concessioni", format="%d"),
        "importo_totale": st.column_config.NumberColumn("Importo totale", format="€%.0f"),
    }, hide_index=True, width="stretch")

st.markdown("---")

# -- Tipo di procedimento
st.subheader("📋 Aiuti per tipo di procedimento")

proc = rna_per_procedimento()
if not proc.empty:
    col1, col2 = st.columns(2)
    with col1:
        chart = (
            alt.Chart(proc)
            .mark_bar(color="#22c55e")
            .encode(
                y=alt.Y("procedimento:N", title=None, sort="-x"),
                x=alt.X("n_beneficiari:Q", title="Beneficiari"),
                tooltip=["procedimento", "n_beneficiari", "importo_totale"],
            )
            .properties(height=200)
        )
        st.altair_chart(chart, width="stretch")
    with col2:
        st.dataframe(proc, column_config={
            "procedimento": "Procedimento",
            "n_beneficiari": st.column_config.NumberColumn("Beneficiari", format="%d"),
            "n_concessioni": st.column_config.NumberColumn("Concessioni", format="%d"),
            "importo_totale": st.column_config.NumberColumn("Importo", format="€%.0f"),
        }, hide_index=True, width="stretch")

st.markdown("---")

# -- Stazioni appaltanti (ANAC)
st.subheader("🏢 Top stazioni appaltanti — Appalti Pubblici")
st.caption("Quali PA lavorano di piu' con gli ETS?")

sa = top_stazioni_appaltanti(20)
if sa.empty:
    st.info("Nessun dato disponibile.")
else:
    chart = (
        alt.Chart(sa)
        .mark_bar(color="#f97316")
        .encode(
            y=alt.Y("stazione_appaltante:N", title=None, sort="-x"),
            x=alt.X("importo_totale:Q", title="Importo totale (€)", axis=alt.Axis(format="~s")),
            tooltip=["stazione_appaltante", "n_ets", "n_appalti", "importo_totale"],
        )
        .properties(height=400)
    )
    st.altair_chart(chart, width="stretch")

    st.dataframe(sa, column_config={
        "stazione_appaltante": "Stazione appaltante",
        "n_ets": st.column_config.NumberColumn("ETS coinvolti", format="%d"),
        "n_appalti": st.column_config.NumberColumn("Appalti", format="%d"),
        "importo_totale": st.column_config.NumberColumn("Importo totale", format="€%.0f"),
    }, hide_index=True, width="stretch")
