"""Terzo Settore Intelligence — Dashboard Streamlit."""

import streamlit as st

st.set_page_config(
    page_title="Terzo Settore · Intelligence",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = {
    "": [
        st.Page("pages/01_Panoramica.py", title="Panoramica", icon="📊", default=True),
    ],
    "Esplora": [
        st.Page("pages/02_Anagrafe.py", title="Anagrafe", icon="📋"),
        st.Page("pages/03_Trasparenza.py", title="Trasparenza", icon="🔍"),
        st.Page("pages/04_Programmi.py", title="Programmi", icon="🇪🇺"),
        st.Page("pages/05_CinquePerMille.py", title="5×1000", icon="💰"),
        st.Page("pages/09_Territorio.py", title="Territorio", icon="🗺️"),
        st.Page("pages/10_Censimento.py", title="Censimento 2023", icon="🏛️"),
    ],
    "Dettaglio": [
        st.Page("pages/06_Scheda_ETS.py", title="Scheda ETS", icon="🔎"),
        st.Page("pages/07_Bandi.py", title="Bandi", icon="📢"),
        st.Page("pages/08_Matching.py", title="Matching", icon="🎯"),
    ],
    "Strumenti": [
        st.Page("pages/11_SQL.py", title="Query SQL", icon="🛠️"),
    ],
}

pg = st.navigation(pages, position="sidebar")
st.sidebar.markdown("---")
st.sidebar.caption("[DataCivicLab](https://dataciviclab.org/)")
pg.run()
