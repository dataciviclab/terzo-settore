-- mart.sql — ETS + RNA
SELECT
    codice_fiscale,
    COUNT(*) as n_concessioni,
    ROUND(SUM(importo), 0) as importo_totale
FROM clean_input
GROUP BY codice_fiscale
