"""Query SQL — Esegui query libere sui dataset."""

import sys

import streamlit as st
from lab_connectors.duckdb import safe_connect

from sources import (
    OUT, RUNTS, MART_ETS, MART_COMUNI, MART_5XMILLE,
    MART_ANAC_AGG, MART_PNRR, MART_RNA, MART_FTS, MART_MEF, MART_COESIONE,
)

# Mappa alias → path parquet
DATASETS = {
    "runts": RUNTS,
    "ets_unified": MART_ETS,
    "ets_comuni": MART_COMUNI,
    "ets_5xmille": MART_5XMILLE,
    "ets_anac": MART_ANAC_AGG,
    "ets_pnrr": MART_PNRR,
    "ets_rna": MART_RNA,
    "ets_fts": MART_FTS,
    "ets_mef": MART_MEF,
    "ets_coesione": MART_COESIONE,
}

st.title("Query SQL")
st.caption("Esegui query DuckDB su tutti i dataset disponibili")

# Selezione dataset
selected = st.multiselect(
    "Dataset da caricare (alias → tabella SQL)",
    options=list(DATASETS.keys()),
    default=["runts", "ets_unified"],
)

if not selected:
    st.warning("Seleziona almeno un dataset.")
    st.stop()

# Costruisci FROM clause
from_parts = []
for name in selected:
    path = DATASETS[name]
    from_parts.append(f"read_parquet('{path}') AS {name}")
from_clause = ", ".join(from_parts)

# Query di esempio
examples = {
    "Conteggio ETS per sezione": f"SELECT sezione, COUNT(*) as enti FROM runts GROUP BY sezione ORDER BY enti DESC",
    "Top 10 ETS per 5x1000": f"SELECT denominazione, comune, importo_5x1000_2025 FROM ets_unified WHERE importo_5x1000_2025 > 0 ORDER BY importo_5x1000_2025 DESC LIMIT 10",
    "Distribuzione capacita": f"SELECT capacita_progettuale, COUNT(*) as enti FROM ets_unified GROUP BY capacita_progettuale ORDER BY enti DESC",
    "Top comuni per ETS": f"SELECT comune, provincia, ets_tot FROM ets_comuni ORDER BY ets_tot DESC LIMIT 10",
}

# Editor SQL
default_query = list(examples.values())[0]
query = st.text_area(
    "SQL query",
    value=default_query,
    height=150,
    placeholder="SELECT ... FROM runts WHERE ...",
)

# Esempio rapido
col1, col2 = st.columns([3, 1])
with col2:
    st.markdown("**Esempi:**")
    for label, sql in examples.items():
        if st.button(label, key=f"ex_{label}"):
            st.session_state["query"] = sql
            st.rerun()

# Esegui
if st.button("Esegui", type="primary"):
    with st.spinner("Esecuzione..."):
        try:
            with safe_connect() as con:
                full_sql = query.replace("FROM _T_", f"FROM {from_clause}")
                # Sostituisci alias nelle FROM clause
                for name in selected:
                    full_sql = full_sql.replace(f"FROM {name}", f"FROM (SELECT * FROM {name})")
                result = con.sql(full_sql).df()
            st.dataframe(result, use_container_width=True, height=400)
            st.caption(f"{len(result)} righe")
        except Exception as e:
            st.error(f"Errore: {e}")
