-- mart_aggiudicazioni.sql — ANAC: aggiudicazioni per CF
SELECT
    codice_fiscale,
    COUNT(*) as n_appalti,
    ROUND(SUM(importo), 0) as importo_totale,
    MAX(CASE WHEN appalto_riservato IS NOT NULL AND appalto_riservato != ''
              AND appalto_riservato != 'LA PARTECIPAZIONE NON È RISERVATA.' THEN 1 ELSE 0 END) as ha_appalti_riservati,
    MAX(CASE WHEN flag_pnrr = true THEN 1 ELSE 0 END) as ha_appalti_pnrr,
    SUM(CASE WHEN appalto_multiplo THEN 1 ELSE 0 END) as appalti_multiparti
FROM clean_input
WHERE fonte = 'anac_aggiudicazione'
GROUP BY codice_fiscale
