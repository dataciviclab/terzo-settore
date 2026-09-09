"""Bandi — Quali bandi sono aperti?"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from pathlib import Path

import streamlit as st
from sources import load_bandi

st.title("📢 Bandi Attivi")

bandi = load_bandi()
if not bandi:
    st.warning("Nessun bando trovato.")
    st.stop()

# ── Filtri
fonts = list({b["fonte"] for b in bandi})
col1, col2 = st.columns(2)
with col1:
    fonte_f = st.selectbox("Fonte", ["Tutte"] + sorted(fonts), key="b_fonte")
with col2:
    search = st.text_input("Cerca", key="b_search")

filtered = bandi
if fonte_f != "Tutte":
    filtered = [b for b in filtered if b["fonte"] == fonte_f]
if search:
    q = search.lower()
    filtered = [b for b in filtered if q in (b["titolo"] + b["ente"]).lower()]

st.write(f"**{len(filtered)} bandi** trovati")

for b in filtered[:50]:
    with st.expander(f"**{b['titolo'][:70]}** — {b['scadenza'][:20]}"):
        st.write(f"**Fonte:** {b['fonte']}")
        st.write(f"**Ente:** {b['ente']}")
        st.write(f"**Scadenza:** {b['scadenza']}")
        if b.get("tag"):
            st.write(f"**Tag:** {', '.join(b['tag'][:5])}")
        if b.get("url"):
            st.markdown(f"🔗 [Apri bando]({b['url']})")
