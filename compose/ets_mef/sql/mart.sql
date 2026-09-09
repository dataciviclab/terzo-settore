-- mart.sql — ETS + MEF
SELECT
    codice_fiscale,
    COUNT(*) as n_immobili,
    ROUND(SUM(importo), 0) as canone_totale
FROM clean_input
GROUP BY codice_fiscale
