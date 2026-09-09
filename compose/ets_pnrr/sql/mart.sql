-- mart.sql — ETS + PNRR
SELECT
    codice_fiscale,
    COUNT(*) as n_progetti,
    ROUND(SUM(importo), 0) as importo_totale
FROM clean_input
GROUP BY codice_fiscale
