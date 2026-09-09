-- mart_partecipazioni.sql — ANAC: partecipazioni per CF
SELECT
    codice_fiscale,
    SUM(n_gare) as gare_partecipate
FROM clean_input
WHERE fonte = 'anac_partecipazione'
GROUP BY codice_fiscale
