-- mart_profilo.sql — profilo per ente (ultimi dati disponibili)
-- Unità di analisi: codice_fiscale (fallback nome se CF mancante).

WITH latest AS (
    SELECT
        COALESCE(codice_fiscale, 'NOME:' || nome_organizzazione) AS ente_key,
        codice_fiscale,
        nome_organizzazione,
        url_scheda,
        anno_dati,
        bilancio_entrate,
        is_bilancio_outlier,
        fondi_istituzionali,
        fondi_privati,
        fondi_5x1000,
        progetti_diretti,
        progetti_indiretti,
        beneficiari,
        dipendenti_italia,
        dipendenti_estero,
        volontari_totali,
        numero_donatori,
        is_aics,
        is_ets,
        compliance_231,
        organo_controllo_interno,
        codice_etico,
        provincia,
        citta,
        forma_giuridica,
        ROW_NUMBER() OVER (
            PARTITION BY COALESCE(codice_fiscale, 'NOME:' || nome_organizzazione)
            ORDER BY anno_dati DESC NULLS LAST
        ) AS rn
    FROM clean_input
)
SELECT
    ente_key,
    codice_fiscale,
    nome_organizzazione,
    url_scheda,
    anno_dati AS anno_ultimi_dati,
    bilancio_entrate,
    COALESCE(is_bilancio_outlier, FALSE) AS is_bilancio_outlier,
    fondi_istituzionali,
    fondi_privati,
    fondi_5x1000,
    progetti_diretti,
    progetti_indiretti,
    beneficiari,
    dipendenti_italia,
    dipendenti_estero,
    volontari_totali,
    numero_donatori,
    is_aics,
    is_ets,
    compliance_231,
    organo_controllo_interno,
    codice_etico,
    provincia,
    citta,
    forma_giuridica
FROM latest
WHERE rn = 1
