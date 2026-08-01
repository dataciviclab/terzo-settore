"""DataCivicLab — Terzo Settore Intelligence Dashboard"""

import json
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]

st.set_page_config(page_title="TSI Dashboard", layout="wide")
st.title("📡 Terzo Settore Intelligence")
st.caption("Dati RUNTS, ANAC, 5x1000, PNRR — DataCivicLab")


# ── Caricamento dati ────────────────────────────────────────────────

@st.cache_resource
def load_comuni():
    return duckdb.connect().sql(
        f"SELECT * FROM '{ROOT / 'data/comuni_ets.parquet'}'"
    ).fetchdf()

@st.cache_resource
def load_bandi():
    path = ROOT / "cruscotto/radar-completo.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)

@st.cache_resource
def search_ets(q: str):
    if not q or len(q) < 2:
        return pd.DataFrame()
    con = duckdb.connect()
    df = con.sql(f"""
        SELECT codice_fiscale, denominazione, sezione, comune, provincia,
               capacita_progettuale,
               importo_5x1000_2025, ha_finanziamenti_ue, ha_progetti_pnrr,
               ha_appalti_pubblici, numero_appalti,
               temi_anac
        FROM '{ROOT / 'data/unified_ets.parquet'}'
        WHERE lower(denominazione) LIKE '%{q.lower()}%'
        ORDER BY importo_5x1000_2025 DESC NULLS LAST
        LIMIT 30
    """).fetchdf()
    con.close()
    return df


# ── Sidebar ─────────────────────────────────────────────────────────

st.sidebar.header("Filtri")


# ── TAB 1: Territorio ──────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs(["🗺️ Territorio", "📋 Bandi", "🏛️ ETS"])

with tab1:
    df = load_comuni()
    min_ets = st.sidebar.slider("Min ETS per comune", 0, 500, 10)

    # Aggrega per provincia
    prov = df[df["ets_tot"] >= min_ets].groupby("provincia", as_index=False).agg(
        ett=("ets_tot", "sum"),
        ets_matchabili=("ets_matchabili", "sum"),
        appalti=("appalti_riservati", "sum"),
        comuni=("comune", "nunique"),
    )
    prov.columns = ["provincia", "ets_tot", "ets_matchabili", "appalti_riservati", "comuni"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Comuni", f"{len(df):,}")
    col2.metric("ETS totali", f"{df['ets_tot'].sum():,}")
    col3.metric("ETS matchabili", f"{df['ets_matchabili'].sum():,}")
    col4.metric("Appalti riservati", f"{df['appalti_riservati'].sum():,}")

    fig = px.bar(
        prov.sort_values("ets_tot", ascending=False).head(20),
        x="provincia", y="ets_tot", color="ets_matchabili",
        title="ETS per provincia (top 20)",
        labels={"ets_tot": "ETS totali", "ets_matchabili": "ETS matchabili", "provincia": ""},
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tabella gap
    st.subheader("🚩 Gap territoriali")
    gap = df[
        (df["appalti_riservati"] >= 5) & (df["ets_matchabili"] < 5)
    ].sort_values("appalti_riservati", ascending=False).head(10)
    if not gap.empty:
        st.dataframe(
            gap[["comune", "provincia", "appalti_riservati", "ets_matchabili", "ets_tot", "rd_pct"]],
            column_config={
                "appalti_riservati": st.column_config.NumberColumn(format="%d"),
                "rd_pct": st.column_config.NumberColumn(format="%.1f%%"),
            },
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("Nessun gap critico rilevato.")


# ── TAB 2: Bandi ──────────────────────────────────────────────────

with tab2:
    scan = load_bandi()
    if not scan:
        st.warning("Nessun dato bandi. Esegui `make scan` prima.")
        st.stop()

    bandi_df = pd.DataFrame([
        {
            "titolo": r["titolo"],
            "ente": r.get("ente", ""),
            "budget": r.get("budget", 0),
            "scadenza": r.get("scadenza", ""),
            "gg": r.get("gg_rimasti", r.get("gg", 999)),
            "status": r["status"],
            "tags": ", ".join(r.get("tags", [])),
            "territorio": ", ".join(r.get("territorio", [])),
            "n_candidati": len(r.get("candidati", [])),
        }
        for r in scan["resultados"]
    ])

    # Filtri
    all_tags = set()
    for r in scan["resultados"]:
        all_tags.update(r.get("tags", []))
    selected_tag = st.sidebar.selectbox("Tag", ["Tutti"] + sorted(all_tags))
    urgenza = st.sidebar.selectbox("Urgenza", ["Tutte", "≤30gg", "≤60gg", "≤90gg"])

    filtered = bandi_df.copy()
    if selected_tag != "Tutti":
        filtered = filtered[filtered["tags"].str.contains(selected_tag, na=False)]
    if urgenza == "≤30gg":
        filtered = filtered[(filtered["gg"] >= 0) & (filtered["gg"] <= 30)]
    elif urgenza == "≤60gg":
        filtered = filtered[(filtered["gg"] >= 0) & (filtered["gg"] <= 60)]
    elif urgenza == "≤90gg":
        filtered = filtered[(filtered["gg"] >= 0) & (filtered["gg"] <= 90)]

    st.metric("Bandi attivi", f"{len(bandi_df)}  ({len(filtered)} filtrati)")

    for _, r in filtered.sort_values("gg").iterrows():
        urg = "🔴" if 0 <= r["gg"] <= 30 else "🟡" if r["gg"] <= 60 else "🟢"
        budget = f" — €{r['budget']:,.0f}" if r["budget"] else ""
        with st.expander(f"{urg} {r['titolo'][:90]} (scad. {r['scadenza']}, {r['gg']}gg{budget})"):
            st.markdown(f"**Ente**: {r['ente']}")
            st.markdown(f"**Stato**: {r['status']} | **Candidati**: {r['n_candidati']} | **Territorio**: {r['territorio']}")
            st.markdown(f"**Tag**: {r['tags']}")


# ── TAB 3: ETS ────────────────────────────────────────────────────

with tab3:
    q = st.text_input("Cerca ETS per nome (almeno 2 caratteri)", placeholder="es. Nazareno")
    if q and len(q) >= 2:
        df_ets = search_ets(q)
        if df_ets.empty:
            st.warning("Nessun ETS trovato.")
        else:
            st.success(f"{len(df_ets)} ETS trovati")
            for _, r in df_ets.iterrows():
                with st.expander(f"{r['denominazione'][:70]} — {r['comune']} ({r['provincia']})"):
                    cols = st.columns(3)
                    cols[0].metric("Sezione", r["sezione"][:25] if r["sezione"] else "—")
                    cols[0].metric("Capacità", r["capacita_progettuale"])
                    cols[1].metric("5x1000 2025", f"€{r['importo_5x1000_2025']:,.0f}" if r["importo_5x1000_2025"] and r["importo_5x1000_2025"] > 0 else "—")
                    cols[1].metric("Finanziamenti UE", "✅" if r["ha_finanziamenti_ue"] else "❌")
                    cols[2].metric("Progetti PNRR", "✅" if r["ha_progetti_pnrr"] else "❌")
                    cols[2].metric("Appalti pubblici", f"{r['numero_appalti']} app." if r["numero_appalti"] and r["numero_appalti"] > 0 else "—")
                    if r["temi_anac"] and r["temi_anac"] != "":
                        st.caption(f"🏷️ Temi: {r['temi_anac']}")
    else:
        st.info("Inserisci almeno 2 caratteri per cercare.")


# ── Footer ─────────────────────────────────────────────────────────

st.markdown("---")
st.caption("Dati aggiornati al RUNTS + ANAC + 5x1000 + PNRR — [DataCivicLab](https://github.com/dataciviclab)")
