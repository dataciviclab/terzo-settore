"""Matching — Trova ETS candidati per un bando."""


import streamlit as st
from sources import load_bandi, match_bandi_ets

st.title("Matching Bandi <-> ETS")
st.caption("Trova gli ETS piu adatti per un bando in base all'esperienza pregressa")

# -- Carica bandi
bandi = load_bandi()

if not bandi:
    st.warning("Nessun bando disponibile. Esegui `make bandi` per aggiornare.")
    st.stop()

# -- Selezione bando
st.subheader("Seleziona un bando")

options = [f"{b['titolo'][:80]}..." if len(b['titolo']) > 80 else b['titolo'] for b in bandi]
sel_idx = st.selectbox("Bando", range(len(options)), format_func=lambda x: options[x], key="bando_sel")

bando = bandi[sel_idx]
tags = bando.get("tag", [])

# -- Dettagli bando
st.markdown("---")
st.subheader("Dettagli bando")

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"**{bando['titolo']}**")
    st.caption(f"Ente: {bando.get('ente_erogatore', '-')}")
    if bando.get('scadenza'):
        st.caption(f"Scadenza: {bando['scadenza'][:80]}")
with col2:
    if tags:
        st.markdown("**Tag:**")
        st.write(tags)

# -- Esegui matching
st.markdown("---")
st.subheader("Top ETS candidati")

if not tags:
    st.warning("Nessun tag disponibile per questo bando.")
    st.stop()

results = match_bandi_ets(bando, top_n=20)

if results.empty:
    st.info("Nessun ETS trovato con esperienza in questi temi.")
else:
    st.dataframe(results[[
        "denominazione", "sezione", "comune", "provincia",
        "capacita_progettuale", "n_appalti", "anni_5x1000",
        "score",
    ]], column_config={
        "denominazione": "Denominazione",
        "sezione": "Sezione",
        "comune": "Comune",
        "provincia": "Prov",
        "capacita_progettuale": " capacita",
        "n_appalti": "Appalti",
        "anni_5x1000": "Anni 5x1000",
        "score": st.column_config.NumberColumn("Score", format="%.1f"),
    }, hide_index=True, width="stretch")

    # Score breakdown primo risultato
    if len(results) > 0:
        st.markdown("---")
        st.subheader("Score breakdown - primo risultato")
        r = results.iloc[0]
        st.markdown(f"**{r['denominazione']}** ({r['comune']}, {r['provincia']})")
        c1, c2, c3 = st.columns(3)
        c1.metric("Tema", f"{r['tema_score']:.0f}")
        c2.metric(" capacita", f"{r['capacity_bonus']:.0f}")
        c3.metric("Score totale", f"{r['score']:.0f}")
