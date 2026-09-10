"""Censimento ISTAT Non Profit 2023 — Dati regionali e provinciali."""

import altair as alt
import streamlit as st
from sources import (
    istat_2023_kpi,
    istat_2023_province,
    istat_2023_regioni,
    istat_2023_settori,
)

st.header("🏛️ Censimento ISTAT Non Profit 2023")
st.caption("Fonte: ISTAT — Tavole statistiche 2023 (dati definitivi)")

# -- KPI nazionali -------------------------------------------------------
kpi = istat_2023_kpi()
if not kpi.empty:
    ist_tot = int(kpi.iloc[0]["istituzioni_totali"] or 0)
    dip_tot = int(kpi.iloc[0]["dipendenti_totali"] or 0)
    c1, c2, c3 = st.columns(3)
    c1.metric("Istituzioni non profit", f"{ist_tot:,}".replace(",", "."))
    c2.metric("Dipendenti", f"{dip_tot:,}".replace(",", "."))
    c3.metric("Media dipendenti / istituzione", f"{dip_tot / ist_tot:.1f}" if ist_tot else "-")

st.divider()

# -- Regioni: bar chart --------------------------------------------------
st.subheader("📍 Per regione")
df_reg = istat_2023_regioni()
if not df_reg.empty:
    tab1, tab2 = st.tabs(["Bar chart", "Tabella"])
    with tab1:
        # Unpivot per Altair
        df_melt = df_reg.melt(
            id_vars=["regione", "istituzioni_totali"],
            value_vars=["associazioni", "cooperative", "fondazioni", "altra_forma"],
            var_name="forma_giuridica", value_name="n",
        )
        ordine = df_reg.sort_values("istituzioni_totali", ascending=False)["regione"].tolist()
        chart = (
            alt.Chart(df_melt)
            .mark_bar()
            .encode(
                y=alt.Y("regione:N", sort=ordine, title=None),
                x=alt.X("n:Q", title="Istituzioni"),
                color=alt.Color("forma_giuridica:N", title="Forma giuridica"),
                tooltip=["regione", "forma_giuridica", "n"],
            )
            .properties(height=600)
        )
        st.altair_chart(chart, width="stretch")
    with tab2:
        st.dataframe(df_reg, width="stretch", hide_index=True)

st.divider()

# -- Settori: bar chart --------------------------------------------------
st.subheader("🎯 Per settore di attività")
df_set = istat_2023_settori()
if not df_set.empty:
    settore_tot = (
        df_set.groupby("settore", as_index=False)["istituzioni"].sum()
        .sort_values("istituzioni", ascending=False)
    )
    ordine = settore_tot["settore"].tolist()
    chart = (
        alt.Chart(settore_tot)
        .mark_bar()
        .encode(
            y=alt.Y("settore:N", sort=ordine, title=None),
            x=alt.X("istituzioni:Q", title="Istituzioni"),
            tooltip=["settore", "istituzioni"],
        )
        .properties(height=500)
    )
    st.altair_chart(chart, width="stretch")

st.divider()

# -- Province: tabella + distribuzione ------------------------------------
st.subheader("🏘️ Per provincia")
df_prov = istat_2023_province()
if not df_prov.empty:
    col_filter, col_chart = st.columns([1, 2])
    with col_filter:
        search = st.text_input("Cerca provincia", "")
        filtered = df_prov
        if search:
            filtered = df_prov[df_prov["provincia"].str.contains(search, case=False, na=False)]
        st.dataframe(filtered, width="stretch", hide_index=True, height=400)
    with col_chart:
        top20 = df_prov.sort_values("istituzioni", ascending=False).head(20)
        ordine = top20["provincia"].tolist()
        chart = (
            alt.Chart(top20)
            .mark_bar()
            .encode(
                y=alt.Y("provincia:N", sort=ordine, title=None),
                x=alt.X("istituzioni:Q", title="Istituzioni"),
                tooltip=["provincia", "istituzioni", "dipendenti"],
            )
            .properties(height=400)
        )
        st.altair_chart(chart, width="stretch")
