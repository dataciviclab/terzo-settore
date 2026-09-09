-- mart_subappalti.sql — ANAC: subappalti per CF
SELECT
    codice_fiscale,
    COUNT(*) as n_subappalti
FROM clean_input
WHERE fonte = 'anac_subappalto'
GROUP BY codice_fiscale
