-- clean.sql — Open Cooperazione (OSC cooperazione allo sviluppo)
-- Input: raw_input CSV tidy prodotto da scripts/fetch_open_cooperazione.py
--   (latin-1 -> utf-8, join CF, numeri italiani -> punti decimali, flag SI/NO)
--
-- Output: tipizzato + aggregati HR. Colonne free-text non usate dal compose
--   (social, PDF, reti lunghe) sono droppate qui — il raw le lascia disponibili
--   se serviranno in futuro (lens transizione: info non perse a monte).
--
-- Cast: macro toolkit (cast_int / cast_double / cast_bigint) — stesso contratto
--   di ade-cinque-per-mille e degli altri dataset del repo.
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
    cast_int(anno_dati) AS anno_dati,
    cast_int(anno_bilancio) AS anno_bilancio,
    cast_int(anno_risorse_umane) AS anno_risorse_umane,
    normalize_string(indirizzo) AS indirizzo,
    normalize_string(citta) AS citta,
    UPPER(normalize_string(provincia)) AS provincia,
    normalize_string(cap) AS cap,
    normalize_string(email) AS email,
    normalize_string(telefono) AS telefono,
    cast_int(anno_fondazione) AS anno_fondazione,
    normalize_string(forma_giuridica) AS forma_giuridica,
    decode_flag(is_ets, 'SI') AS is_ets,
    decode_flag(is_aics, 'SI') AS is_aics,
    normalize_string(reti) AS reti,
    normalize_string(sitoweb) AS sitoweb,
    normalize_string(sdgs) AS sdgs,
    normalize_string(rappresentante_nome) AS rappresentante_nome,
    normalize_string(rappresentante_cognome) AS rappresentante_cognome,
    UPPER(normalize_string(rappresentante_sesso)) AS rappresentante_sesso,
    cast_int(rappresentante_anno_in_carica) AS rappresentante_anno_in_carica,
    normalize_string(segretario_nome) AS segretario_nome,
    normalize_string(segretario_cognome) AS segretario_cognome,
    cast_int(numero_associati) AS numero_associati,
    decode_flag(organo_controllo_interno, 'SI') AS organo_controllo_interno,
    decode_flag(ecosoc, 'SI') AS ecosoc,
    decode_flag(compliance_231, 'SI') AS compliance_231,
    normalize_string(certificazioni) AS certificazioni,
    normalize_string(partenariati_enti_pubblici) AS partenariati_enti_pubblici,
    decode_flag(codice_etico, 'SI') AS codice_etico,
    decode_flag(pianificazione_strategica, 'SI') AS pianificazione_strategica,
    cast_double(bilancio_entrate) AS bilancio_entrate,
    cast_double(bilancio_uscite) AS bilancio_uscite,
    -- Outlier nota fonte: >1 mld non e' plausibile per OSC di cooperazione
    cast_double(bilancio_entrate) > 1000000000 AS is_bilancio_outlier,
    decode_flag(bilancio_certificato, 'SI') AS bilancio_certificato,
    cast_double(oneri_missione) AS oneri_missione,
    cast_double(oneri_struttura) AS oneri_struttura,
    cast_double(oneri_raccolta_fondi) AS oneri_raccolta_fondi,
    cast_int(numero_donatori) AS numero_donatori,
    cast_double(fondi_istituzionali) AS fondi_istituzionali,
    cast_double(fondi_privati) AS fondi_privati,
    cast_double(fondi_aziende) AS fondi_aziende,
    cast_double(fondi_fondazioni) AS fondi_fondazioni,
    cast_double(fondi_chiese) AS fondi_chiese,
    cast_double(fondi_5x1000) AS fondi_5x1000,
    cast_int(firme_5x1000) AS firme_5x1000,
    decode_flag(adozioni_distanza, 'SI') AS adozioni_distanza,
    cast_int(numero_adozioni_attive) AS numero_adozioni_attive,
    normalize_string(principali_finanziatori_pubblici) AS principali_finanziatori_pubblici,
    decode_flag(bilancio_sociale, 'SI') AS bilancio_sociale,
    decode_flag(valutazione_impatto, 'SI') AS valutazione_impatto,
    cast_int(dipendenti_italia) AS dipendenti_italia,
    cast_int(dipendenti_estero) AS dipendenti_estero,
    cast_int(volontari_servizio_civile) AS volontari_servizio_civile,
    cast_int(volontari_totali) AS volontari_totali,
    cast_int(progetti_diretti) AS progetti_diretti,
    cast_int(progetti_indiretti) AS progetti_indiretti,
    cast_bigint(beneficiari) AS beneficiari,
    normalize_string(stato_dati_annuale) AS stato_dati_annuale
FROM raw_input
WHERE normalize_string(nome_organizzazione) IS NOT NULL
  AND cast_int(anno_dati) IS NOT NULL
