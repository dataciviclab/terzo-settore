-- clean.sql — Open Cooperazione (OSC cooperazione allo sviluppo)
-- Input: raw_input CSV tidy prodotto da scripts/fetch_open_cooperazione.py
--   (latin-1 -> utf-8, join CF, numeri italiani -> punti decimali, flag SI/NO)
--
-- Output: tipizzato + aggregati HR. Colonne free-text non usate dal compose
--   (social, PDF, reti lunghe) sono droppate qui — il raw le lascia disponibili
--   se serviranno in futuro (lens transizione: info non perse a monte).
--
-- Caveat: dati autodichiarati, campione OSC (~150-160 orgs/anno), non tutto
--   il terzo settore. CF nullable per org senza scheda scrapata.
--
-- Qualità: flag is_bilancio_outlier per entrate > 1 mld € (fuori scala per
--   questo settore; es. S. Egidio 2025 = 3.4 mld su serie 20-32 mln → errore
--   di inserimento alla fonte, non del parser). Il dato raw resta nel clean;
--   i totali analitici devono filtrare il flag.

SELECT
    normalize_string(codice_fiscale) AS codice_fiscale,
    normalize_string(nome_organizzazione) AS nome_organizzazione,
    normalize_string(url_scheda) AS url_scheda,
    TRY_CAST(anno_dati AS INTEGER) AS anno_dati,
    TRY_CAST(anno_bilancio AS INTEGER) AS anno_bilancio,
    TRY_CAST(anno_risorse_umane AS INTEGER) AS anno_risorse_umane,
    normalize_string(indirizzo) AS indirizzo,
    normalize_string(citta) AS citta,
    UPPER(normalize_string(provincia)) AS provincia,
    normalize_string(cap) AS cap,
    normalize_string(email) AS email,
    normalize_string(telefono) AS telefono,
    TRY_CAST(anno_fondazione AS INTEGER) AS anno_fondazione,
    normalize_string(forma_giuridica) AS forma_giuridica,
    decode_flag(is_ets, 'SI') AS is_ets,
    decode_flag(is_aics, 'SI') AS is_aics,
    normalize_string(reti) AS reti,
    normalize_string(sitoweb) AS sitoweb,
    normalize_string(sdgs) AS sdgs,
    normalize_string(rappresentante_nome) AS rappresentante_nome,
    normalize_string(rappresentante_cognome) AS rappresentante_cognome,
    UPPER(normalize_string(rappresentante_sesso)) AS rappresentante_sesso,
    TRY_CAST(rappresentante_anno_in_carica AS INTEGER) AS rappresentante_anno_in_carica,
    normalize_string(segretario_nome) AS segretario_nome,
    normalize_string(segretario_cognome) AS segretario_cognome,
    TRY_CAST(numero_associati AS INTEGER) AS numero_associati,
    decode_flag(organo_controllo_interno, 'SI') AS organo_controllo_interno,
    decode_flag(ecosoc, 'SI') AS ecosoc,
    decode_flag(compliance_231, 'SI') AS compliance_231,
    normalize_string(certificazioni) AS certificazioni,
    normalize_string(partenariati_enti_pubblici) AS partenariati_enti_pubblici,
    decode_flag(codice_etico, 'SI') AS codice_etico,
    decode_flag(pianificazione_strategica, 'SI') AS pianificazione_strategica,
    TRY_CAST(bilancio_entrate AS DOUBLE) AS bilancio_entrate,
    TRY_CAST(bilancio_uscite AS DOUBLE) AS bilancio_uscite,
    -- Outlier nota fonte: >1 mld non e' plausibile per OSC di cooperazione
    TRY_CAST(bilancio_entrate AS DOUBLE) > 1000000000 AS is_bilancio_outlier,
    decode_flag(bilancio_certificato, 'SI') AS bilancio_certificato,
    TRY_CAST(oneri_missione AS DOUBLE) AS oneri_missione,
    TRY_CAST(oneri_struttura AS DOUBLE) AS oneri_struttura,
    TRY_CAST(oneri_raccolta_fondi AS DOUBLE) AS oneri_raccolta_fondi,
    TRY_CAST(numero_donatori AS INTEGER) AS numero_donatori,
    TRY_CAST(fondi_istituzionali AS DOUBLE) AS fondi_istituzionali,
    TRY_CAST(fondi_privati AS DOUBLE) AS fondi_privati,
    TRY_CAST(fondi_aziende AS DOUBLE) AS fondi_aziende,
    TRY_CAST(fondi_fondazioni AS DOUBLE) AS fondi_fondazioni,
    TRY_CAST(fondi_chiese AS DOUBLE) AS fondi_chiese,
    TRY_CAST(fondi_5x1000 AS DOUBLE) AS fondi_5x1000,
    TRY_CAST(firme_5x1000 AS INTEGER) AS firme_5x1000,
    decode_flag(adozioni_distanza, 'SI') AS adozioni_distanza,
    TRY_CAST(numero_adozioni_attive AS INTEGER) AS numero_adozioni_attive,
    normalize_string(principali_finanziatori_pubblici) AS principali_finanziatori_pubblici,
    decode_flag(bilancio_sociale, 'SI') AS bilancio_sociale,
    decode_flag(valutazione_impatto, 'SI') AS valutazione_impatto,
    TRY_CAST(dipendenti_italia AS INTEGER) AS dipendenti_italia,
    TRY_CAST(dipendenti_estero AS INTEGER) AS dipendenti_estero,
    TRY_CAST(volontari_servizio_civile AS INTEGER) AS volontari_servizio_civile,
    TRY_CAST(volontari_totali AS INTEGER) AS volontari_totali,
    TRY_CAST(progetti_diretti AS INTEGER) AS progetti_diretti,
    TRY_CAST(progetti_indiretti AS INTEGER) AS progetti_indiretti,
    TRY_CAST(beneficiari AS BIGINT) AS beneficiari,
    normalize_string(stato_dati_annuale) AS stato_dati_annuale
FROM raw_input
WHERE normalize_string(nome_organizzazione) IS NOT NULL
  AND TRY_CAST(anno_dati AS INTEGER) IS NOT NULL
