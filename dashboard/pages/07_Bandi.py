"""Bandi — Quali bandi sono aperti?"""


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
    filtered = [b for b in filtered if q in ((b.get("titolo") or "") + (b.get("ente") or "")).lower()]

st.write(f"**{len(filtered)} bandi** trovati")

for b in filtered[:50]:
    titolo = (b.get("titolo") or "Senza titolo")[:70]
    scadenza = (b.get("scadenza") or "N/D")[:20]
    with st.expander(f"**{titolo}** — {scadenza}"):
        st.write(f"**Fonte:** {b.get('fonte', 'N/D')}")
        st.write(f"**Ente:** {b.get('ente', 'N/D')}")
        st.write(f"**Scadenza:** {b.get('scadenza', 'N/D')}")
        if b.get("tag"):
            st.write(f"**Tag:** {', '.join(b['tag'][:5])}")
        if b.get("url"):
            st.markdown(f"🔗 [Apri bando]({b['url']})")
