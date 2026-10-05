"""Cooperazione — OSC italiane nella cooperazione allo sviluppo (Open Cooperazione).

Dati autodichiarati (non tutto il terzo settore): ~150 orgs/anno, ~250 profili.
"""

import altair as alt
import pandas as pd
import streamlit as st
from sources import (
    coop_cerca,
    coop_cross_fonti,
    coop_fonti_finanziamento,
    coop_governance,
    coop_kpi,
    coop_outliers,
    coop_territorio,
    coop_top_capacita,
    coop_trend,
    fmt_eur,
    fmt_num,
)

st.title("🌍 Cooperazione internazionale")
st.caption(
    "OSC italiane nella cooperazione allo sviluppo e aiuto umanitario — "
    "Open Cooperazione (dati autodichiarati, CC BY). Non è tutto il terzo settore."
)

try:
    kpi = coop_kpi()
except Exception as e:  # noqa: BLE001
    st.error(f"Dati Open Cooperazione non disponibili: {e}")
    st.stop()

# -- KPI -----------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("📋 Organizzazioni", fmt_num(kpi["enti"]))
c2.metric("🏛️ Iscritte AICS", fmt_num(kpi["aics"]))
c3.metric("💰 Entrate (no outlier)", fmt_eur(kpi["bilancio_tot"]))
c4.metric("🌍 Progetti diretti", fmt_num(int(kpi["progetti"])))

c5, c6, c7, c8 = st.columns(4)
c5.metric("👥 Beneficiari", fmt_num(int(kpi["beneficiari"])))
c6.metric("🧑‍💼 Dipendenti estero", fmt_num(int(kpi["dip_estero"])))
c7.metric("🤲 Volontari", fmt_num(int(kpi["volontari"])))
c8.metric("📅 Anni coperti", f"{min(kpi['anni'])}–{max(kpi['anni'])}")

if kpi.get("outlier_bilancio"):
    st.caption(
        f"Profilo con CF: {kpi['con_cf']}/{kpi['enti']} · "
        f"mediana entrate: {fmt_eur(kpi['bilancio_mediana'])} · "
        f"⚠️ {kpi['outlier_bilancio']} bilancio outlier (entrate > 1 mld, "
        "esclusi dai totali — vedi Qualità dati)."
    )
else:
    st.caption(
        f"Profilo con CF: {kpi['con_cf']}/{kpi['enti']} · "
        f"mediana entrate: {fmt_eur(kpi['bilancio_mediana'])}."
    )

# Nota qualità (outlier fonte)
_out = coop_outliers()
if not _out.empty:
    with st.expander(f"⚠️ Qualità dati — {_out.shape[0]} bilancio outlier", expanded=False):
        st.markdown(
            "Valori **autodichiarati** alla fonte che risultano fuori scala per il "
            "settore (entrate > 1 mld €). Restano nel dataset per tracciabilità; "
            "qui sono esclusi da KPI e totali. "
            "**Esempio**: Comunità di S. Egidio — serie 2019-2024 a 20-32 mln €, "
            "nel 2025 la fonte pubblica ~3,4 mld (errore di inserimento, verificato "
            "sul sito)."
        )
        st.dataframe(
            _out.assign(
                bilancio_entrate=_out["bilancio_entrate"].map(
                    lambda x: fmt_eur(x) if pd.notna(x) else "—"
                )
            ),
            hide_index=True,
            width="stretch",
        )

st.markdown("---")

# -- Trend ---------------------------------------------------------------
st.subheader("📈 Andamento del settore")
st.caption("Organizzazioni con dati inseriti e totale entrate per anno (autodichiarato).")

trend = coop_trend()
if not trend.empty:
    left, right = st.columns(2)
    with left:
        chart = (
            alt.Chart(trend)
            .mark_bar(color="#3b82f6")
            .encode(
                x=alt.X("anno_dati:O", title="Anno"),
                y=alt.Y("enti:Q", title="Organizzazioni"),
                tooltip=["anno_dati", "enti", "bilancio", "progetti"],
            )
            .properties(height=280)
        )
        st.altair_chart(chart, width="stretch")
    with right:
        chart = (
            alt.Chart(trend)
            .mark_line(color="#22c55e", point=True)
            .encode(
                x=alt.X("anno_dati:O", title="Anno"),
                y=alt.Y("bilancio:Q", title="Entrate totali (€)", axis=alt.Axis(format="~s")),
                tooltip=["anno_dati", "enti", alt.Tooltip("bilancio:Q", format=",.0f")],
            )
            .properties(height=280)
        )
        st.altair_chart(chart, width="stretch")

    st.dataframe(
        trend.assign(
            bilancio=trend["bilancio"].map(lambda x: fmt_eur(x)),
            progetti=trend["progetti"].map(lambda x: fmt_num(int(x))),
            beneficiari=trend["beneficiari"].map(lambda x: fmt_num(int(x))),
        ),
        hide_index=True,
        width="stretch",
    )

st.markdown("---")

# -- Territorio ----------------------------------------------------------
st.subheader("🗺️ Dove sono le OSC")
st.caption("Provincia delle sedi — concentrazione Roma/Milano tipica del settore.")

terr = coop_territorio()
if not terr.empty:
    chart = (
        alt.Chart(terr)
        .mark_bar(color="#f59e0b")
        .encode(
            y=alt.Y("provincia:N", title=None, sort="-x"),
            x=alt.X("enti:Q", title="Organizzazioni"),
            tooltip=["provincia", "enti", alt.Tooltip("bilancio:Q", format=",.0f"), "progetti"],
        )
        .properties(height=320)
    )
    st.altair_chart(chart, width="stretch")

    st.dataframe(
        terr.assign(bilancio=terr["bilancio"].map(fmt_eur)),
        column_config={
            "provincia": "Provincia",
            "enti": st.column_config.NumberColumn("Org", format="%d"),
            "bilancio": "Entrate (€)",
            "progetti": st.column_config.NumberColumn("Progetti", format="%d"),
        },
        hide_index=True,
        width="stretch",
    )

st.markdown("---")

# -- Fonti + governance ---------------------------------------------------
left, right = st.columns(2)

with left:
    st.subheader("💶 Fonti di finanziamento")
    st.caption("Importi autodichiarati (ultimi dati per ente, valori > 0).")
    fonti = coop_fonti_finanziamento()
    if not fonti.empty:
        chart = (
            alt.Chart(fonti)
            .mark_bar(color="#8b5cf6")
            .encode(
                y=alt.Y("fonte:N", title=None, sort="-x"),
                x=alt.X("importo_totale:Q", title="Importo totale (€)", axis=alt.Axis(format="~s")),
                tooltip=["fonte", "enti", alt.Tooltip("importo_totale:Q", format=",.0f"), "importo_mediana"],
            )
            .properties(height=220)
        )
        st.altair_chart(chart, width="stretch")
        st.dataframe(
            fonti.assign(
                importo_totale=fonti["importo_totale"].map(fmt_eur),
                importo_mediana=fonti["importo_mediana"].map(fmt_eur),
            ),
            hide_index=True,
            width="stretch",
        )

with right:
    st.subheader("🛡️ Governance e qualità")
    st.caption("Indicatori di trasparenza autodichiarati.")
    gov = coop_governance()
    if not gov.empty:
        total = max(int(gov["enti"].max()), 1)
        gov = gov.assign(pct=(gov["enti"] / total * 100).round(1))
        chart = (
            alt.Chart(gov)
            .mark_bar(color="#06b6d4")
            .encode(
                y=alt.Y("voce:N", title=None, sort="-x"),
                x=alt.X("enti:Q", title="Organizzazioni"),
                tooltip=["voce", "enti", "pct"],
            )
            .properties(height=220)
        )
        st.altair_chart(chart, width="stretch")
        st.dataframe(gov, hide_index=True, width="stretch")

st.markdown("---")

# -- Cross fonti ufficiali ------------------------------------------------
st.subheader("🔗 Presenza nelle fonti ufficiali del progetto")
st.caption(
    "Quante di queste OSC risultano anche in RUNTS, 5×1000 ADE, ANAC, RNA. "
    "Il self-report non sostituisce i registri: li integra."
)

cross = coop_cross_fonti()
if not cross.empty:
    chart = (
        alt.Chart(cross)
        .mark_bar(color="#10b981")
        .encode(
            y=alt.Y("fonte:N", title=None, sort="-x"),
            x=alt.X("enti:Q", title="Organizzazioni"),
            tooltip=["fonte", "enti", "pct"],
        )
        .properties(height=240)
    )
    st.altair_chart(chart, width="stretch")
    st.dataframe(
        cross.rename(columns={"fonte": "Fonte", "enti": "Org", "pct": "% OC"}),
        hide_index=True,
        width="stretch",
    )

st.markdown("---")

# -- Top capacità ---------------------------------------------------------
st.subheader("🏆 Capacità progettuale")
st.caption(
    "Score composito: AICS (x2) + entrate > 1M + progetti > 10 + compliance 231 + codice etico. "
    "Indicativo per matching bandi cooperazione."
)

top = coop_top_capacita(15)
if not top.empty:
    st.dataframe(
        top.assign(
            bilancio_entrate=top["bilancio_entrate"].map(
                lambda x: fmt_eur(x) if pd.notna(x) else "—"
            ),
            is_bilancio_outlier=top.get(
                "is_bilancio_outlier", pd.Series([False] * len(top))
            ).map(lambda b: "⚠️" if b else ""),
            progetti_diretti=top["progetti_diretti"].map(
                lambda x: fmt_num(int(x)) if pd.notna(x) else "—"
            ),
            beneficiari=top["beneficiari"].map(
                lambda x: fmt_num(int(x)) if pd.notna(x) else "—"
            ),
            dipendenti_estero=top["dipendenti_estero"].map(
                lambda x: fmt_num(int(x)) if pd.notna(x) else "—"
            ),
        ).rename(
            columns={
                "nome_organizzazione": "Organizzazione",
                "provincia": "Prov",
                "anno_ultimi_dati": "Anno",
                "score": "Score",
                "is_aics": "AICS",
                "bilancio_entrate": "Entrate",
                "is_bilancio_outlier": "Outlier",
                "progetti_diretti": "Progetti",
                "beneficiari": "Beneficiari",
                "dipendenti_estero": "Dip. estero",
                "fondi_istituzionali": "Fondi istit.",
            }
        ),
        hide_index=True,
        width="stretch",
    )

st.markdown("---")

# -- Ricerca --------------------------------------------------------------
st.subheader("🔎 Cerca un'organizzazione")
q = st.text_input("Nome o codice fiscale", key="coop_search")
if q:
    res = coop_cerca(q)
    if res.empty:
        st.info("Nessun risultato.")
    else:
        st.dataframe(
            res[
                [
                    c
                    for c in [
                        "nome_organizzazione",
                        "codice_fiscale",
                        "provincia",
                        "citta",
                        "anno_ultimi_dati",
                        "bilancio_entrate",
                        "progetti_diretti",
                        "is_aics",
                        "url_scheda",
                    ]
                    if c in res.columns
                ]
            ],
            hide_index=True,
            width="stretch",
        )

st.markdown("---")
st.caption(
    "⚠️ **Limiti**: dati autodichiarati da organizzazioni volontarie; campione piccolo "
    "(non tutto il terzo settore); alcuni bilanci possono contenere errori di inserimento "
    "(marcati `is_bilancio_outlier` nel clean). "
    "Fonte: open-cooperazione.it (Info-Cooperazione), licenza CC BY 3.0 IT. "
    "Dataset: `datasets/open-cooperazione/`."
)
