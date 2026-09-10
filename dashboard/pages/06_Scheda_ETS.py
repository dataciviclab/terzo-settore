"""Scheda ETS — Profilo completo di un ente da tutti i compose."""

import streamlit as st
from sources import (
    scheda_ente_profilo, scheda_ente_5xmille, scheda_ente_anac,
    scheda_ente_rna, scheda_ente_pnrr, scheda_ente_fts,
    scheda_ente_mef, scheda_ente_coesione, match_bandi_per_ets, cerca_ente,
)

st.title("Scheda ETS")

query = st.text_input("Cerca per CF o denominazione", placeholder="es. 02031100858", key="ets_q")
if not query:
    st.info("Inserisci un codice fiscale o una denominazione.")
    st.stop()

df = cerca_ente(query)

if df.empty:
    st.warning("Nessun ente trovato.")
    st.stop()

# Selezione ente
if len(df) == 1:
    cf = df.iloc[0]["codice_fiscale"]
    st.caption(f"**{df.iloc[0]['denominazione']}** ({cf})")
else:
    options = [f"{r['denominazione']} — {r['codice_fiscale']}" for _, r in df.iterrows()]
    sel = st.selectbox("Seleziona ente", options, key="ets_sel")
    cf = sel.split(" — ")[-1]

# -- Profilo base
st.markdown("---")
st.subheader("Profilo")
profilo = scheda_ente_profilo(cf)
if not profilo.empty:
    r = profilo.iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Sezione", r.get("sezione", "-"))
    c2.metric("Comune", f"{r.get('comune', '-')} ({r.get('provincia', '-')})")
    c3.metric(" capacita", r.get("capacita_progettuale", "-"))
    if r.get("data_iscrizione"):
        st.caption(f"Iscritto dal: {r['data_iscrizione']}")

# -- 5x1000
try:
    p5 = scheda_ente_5xmille(cf)
    if not p5.empty:
        st.markdown("---")
        st.subheader("5x1000")
        r5 = p5.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Importo totale", f"eur {r5.get('importo_totale', 0):,.0f}")
        c2.metric("Anni", f"{r5.get('anni', 0)}")
        c3.metric("Importo 2025", f"eur {r5.get('importo_2025', 0):,.0f}")
except Exception:
    pass

# -- ANAC
try:
    anac = scheda_ente_anac(cf)
    if anac["aggiudicazioni"] is not None and not anac["aggiudicazioni"].empty:
        st.markdown("---")
        st.subheader("Appalti pubblici (ANAC)")
        st.dataframe(anac["aggiudicazioni"][['n_appalti', 'importo_totale', 'ha_appalti_riservati', 'ha_appalti_pnrr', 'appalti_multiparti']],
                     column_config={"importo_totale": st.column_config.NumberColumn("Importo", format="eur %.0f")},
                     hide_index=True, width="stretch")
except Exception:
    pass

# -- Coesione
try:
    c = scheda_ente_coesione(cf)
    if not c.empty and c.iloc[0].get("ha_progetti_coesione"):
        st.markdown("---")
        st.subheader("Fondi Coesione")
        rc = c.iloc[0]
        col1, col2, col3 = st.columns(3)
        col1.metric("Progetti", f"{int(rc['n_progetti_coesione'])}")
        col2.metric("Temi", f"{int(rc['n_temi_coesione'])}")
        col3.metric("Fascia", rc.get('fascia_coesione', '-'))
except Exception:
    pass

# -- Bandi compatibili
try:
    bandi_match = match_bandi_per_ets(cf)
    if bandi_match:
        st.markdown("---")
        st.subheader("Bandi compatibili")
        for b in bandi_match[:5]:
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{b['titolo'][:80]}**")
                    st.caption(f"{b['ente']}")
                with col2:
                    st.metric("Score", f"{b['score']:.0f}")
                if b.get('scadenza'):
                    st.caption(f"Scadenza: {b['scadenza'][:60]}")
                st.markdown("---")
except Exception:
    pass
