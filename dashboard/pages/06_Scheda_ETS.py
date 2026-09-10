"""Scheda ETS — Profilo completo di un ente da tutti i compose."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from sources import (
    scheda_ente_profilo, scheda_ente_5xmille, scheda_ente_anac,
    scheda_ente_rna, scheda_ente_pnrr, scheda_ente_fts,
    scheda_ente_mef, scheda_ente_coesione, match_bandi_per_ets, MART_ETS,
)
import duckdb

st.title("🔍 Scheda ETS")

query = st.text_input("Cerca per CF o denominazione", placeholder="es. 02031100858", key="ets_q")
if not query:
    st.info("Inserisci un codice fiscale o una denominazione.")
    st.stop()

safe = query.replace("'", "''")
df = duckdb.connect().sql(f"""
    SELECT codice_fiscale, denominazione
    FROM read_parquet('{MART_ETS}')
    WHERE codice_fiscale LIKE '%{safe}%' OR denominazione LIKE '%{safe}%'
    LIMIT 20
""").df()

if df.empty:
    st.warning("Nessun ente trovato.")
    st.stop()

if len(df) == 1:
    cf = df.iloc[0]["codice_fiscale"]
    nome = df.iloc[0]["denominazione"]
else:
    opts = [f"{r['codice_fiscale']} — {r['denominazione']}" for _, r in df.iterrows()]
    sel = st.selectbox("Seleziona ente", opts, key="ets_sel")
    cf = sel.split(" — ")[0]
    nome = sel.split(" — ", 1)[1] if " — " in sel else ""

st.markdown("---")
st.subheader(f"📋 {nome}")
st.caption(f"CF: `{cf}`")

# -- Profilo base
try:
    profilo = scheda_ente_profilo(cf)
    if not profilo.empty:
        r = profilo.iloc[0]

        col1, col2, col3 = st.columns(3)
        col1.metric("Sezione", r.get("sezione", "-"))
        col2.metric("Comune", r.get("comune", "-"))
        col3.metric("Provincia", r.get("provincia", "-"))

        col4, col5, col6 = st.columns(3)
        col4.metric("Regione", r.get("regione", "-"))
        col5.metric("Iscrizione", str(r.get("data_iscrizione", "-"))[:10])
        col6.metric("Capacità", r.get("capacita_progettuale", "-"))
except Exception as e:
    st.warning(f"Profilo non disponibile: {e}")

# -- Riepilogo fonti
st.markdown("---")
st.subheader("📊 Fonti attive")

fonti_attive = []
try:
    p5 = scheda_ente_5xmille(cf)
    if not p5.empty:
        r5 = p5.iloc[0]
        fonti_attive.append(("5×1000", f"€{r5['importo_totale']:,.0f}", f"{int(r5['anni'])} anni",
                             [c for c in ['flag_asd','flag_ricerca_scientifica','flag_ricerca_sanitaria',
                                           'flag_beni_culturali','flag_area_protetta','flag_comune']
                              if r5.get(c)]))
except Exception: pass

try:
    a = scheda_ente_anac(cf)
    if not a["aggiudicazioni"].empty:
        ra = a["aggiudicazioni"].iloc[0]
        dettagli = []
        if int(ra.get('appalti_multiparti', 0)) > 0:
            dettagli.append(f"{int(ra['appalti_multiparti'])} multiparti")
        fonti_attive.append(("ANAC", f"€{ra['importo_totale']:,.0f}", f"{int(ra['n_appalti'])} appalti", dettagli))
except Exception: pass

try:
    r = scheda_ente_rna(cf)
    if not r.empty:
        rr = r.iloc[0]
        fonti_attive.append(("RNA", f"€{rr['importo_totale']:,.0f}", f"{int(rr['n_concessioni'])} concessioni", []))
except Exception: pass

try:
    p = scheda_ente_pnrr(cf)
    if not p.empty:
        rp = p.iloc[0]
        fonti_attive.append(("PNRR", f"€{rp['importo_totale']:,.0f}", f"{int(rp['n_progetti'])} progetti", []))
except Exception: pass

try:
    f = scheda_ente_fts(cf)
    if not f.empty:
        rf = f.iloc[0]
        fonti_attive.append(("Grant UE", f"€{rf['importo_totale']:,.0f}", f"{int(rf['n_grant'])} grant", []))
except Exception: pass

try:
    m = scheda_ente_mef(cf)
    if not m.empty:
        rm = m.iloc[0]
        fonti_attive.append(("Patrimonio", f"€{rm['canone_totale']:,.0f}", f"{int(rm['n_immobili'])} immobili", []))
except Exception: pass

try:
    c = scheda_ente_coesione(cf)
    if not c.empty and c.iloc[0].get("ha_progetti_coesione"):
        rc = c.iloc[0]
        fonti_attive.append(("Coesione", f"{int(rc['n_progetti_coesione'])} progetti",
                             f"{int(rc['n_temi_coesione'])} temi", []))
except Exception: pass

if fonti_attive:
    cols = st.columns(min(len(fonti_attive), 4))
    for i, (nome_f, val, det, tags) in enumerate(fonti_attive):
        col = cols[i % len(cols)]
        with col:
            st.metric(nome_f, val, det)
            if tags:
                st.caption(", ".join(tags))
else:
    st.info("Nessuna fonte trovata per questo ente.")

# -- Dettaglio 5x1000
try:
    p5 = scheda_ente_5xmille(cf)
    if not p5.empty:
        st.markdown("---")
        st.subheader("💰 Dettaglio 5×1000")
        r5 = p5.iloc[0]
        col1, col2, col3 = st.columns(3)
        col1.metric("Importo totale", f"€{r5['importo_totale']:,.0f}")
        col2.metric("Importo 2025", f"€{r5.get('importo_2025', 0):,.0f}")
        col3.metric("Anni", f"{int(r5['anni'])}")

        flags = []
        if r5.get('flag_asd'): flags.append("ASD")
        if r5.get('flag_ricerca_scientifica'): flags.append("Ricerca scientifica")
        if r5.get('flag_ricerca_sanitaria'): flags.append("Ricerca sanitaria")
        if r5.get('flag_beni_culturali'): flags.append("Beni culturali")
        if r5.get('flag_area_protetta'): flags.append("Area protetta")
        if r5.get('flag_comune'): flags.append("Comune")
        if flags:
            st.caption(f"Tipologia: {', '.join(flags)}")
except Exception: pass

# -- Dettaglio RNA
try:
    r = scheda_ente_rna(cf)
    if not r.empty:
        st.markdown("---")
        st.subheader("🏛️ Dettaglio Aiuti di Stato")
        st.dataframe(r[['anno', 'importo', 'soggetto_concedente', 'procedimento']].head(10),
                     column_config={
                         "importo": st.column_config.NumberColumn("Importo", format="€%.0f"),
                     }, hide_index=True, width="stretch")
except Exception: pass

# -- Dettaglio PNRR
try:
    p = scheda_ente_pnrr(cf)
    if not p.empty:
        st.markdown("---")
        st.subheader("🇵🇳 Dettaglio PNRR")
        st.dataframe(p[['anno', 'importo', 'programma', 'descrizione_missione']].head(10),
                     column_config={
                         "importo": st.column_config.NumberColumn("Importo", format="€%.0f"),
                     }, hide_index=True, width="stretch")
except Exception: pass

# -- Dettaglio ANAC
try:
    a = scheda_ente_anac(cf)
    if not a["aggiudicazioni"].empty:
        st.markdown("---")
        st.subheader("🏢 Dettaglio ANAC")
        st.dataframe(a["aggiudicazioni"][['n_appalti', 'importo_totale', 'ha_appalti_riservati', 'ha_appalti_pnrr', 'appalti_multiparti']],
                     column_config={
                         "importo_totale": st.column_config.NumberColumn("Importo", format="€%.0f"),
                     }, hide_index=True, width="stretch")
except Exception: pass

# -- Dettaglio Coesione
try:
    c = scheda_ente_coesione(cf)
    if not c.empty and c.iloc[0].get("ha_progetti_coesione"):
        st.markdown("---")
        st.subheader("🏛️ Dettaglio Fondi Coesione")
        rc = c.iloc[0]
        col1, col2, col3 = st.columns(3)
        col1.metric("Progetti", f"{int(rc['n_progetti_coesione'])}")
        col2.metric("Temi", f"{int(rc['n_temi_coesione'])}")
        col3.metric("Fascia", rc.get('fascia_coesione', '-'))
        if rc.get('temi_coesione'):
            st.caption(f"Temi: {rc['temi_coesione']}")
except Exception: pass

# -- Bandi compatibili
try:
    bandi_match = match_bandi_per_ets(cf)

    if bandi_match:
        st.markdown("---")
        st.subheader("🎯 Bandi compatibili")
        st.caption("Basato su flag 5x1000, capacita e sezione dell'ETS")

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
    else:
        st.info("Nessun bando compatibile trovato.")
except Exception: pass
