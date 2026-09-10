-- mart_per_provincia.sql — 5x1000 per provincia x anno
-- Grain: sigla_provincia x anno
-- Output: enti, importo, split per categoria

SELECT
    anno,
    regione,
    sigla_provincia,
    comune,
    COUNT(DISTINCT codice_fiscale) AS enti,
    COUNT(DISTINCT CASE WHEN flag_ets_onlus THEN codice_fiscale END) AS enti_ets,
    COUNT(DISTINCT CASE WHEN flag_asd THEN codice_fiscale END) AS enti_asd,
    COUNT(DISTINCT CASE WHEN flag_ricerca_scientifica OR flag_ricerca_sanitaria THEN codice_fiscale END) AS enti_ricerca,
    ROUND(SUM(importo_totale_erogabile)::NUMERIC, 0) AS importo_totale,
    ROUND(AVG(importo_totale_erogabile)::NUMERIC, 0) AS importo_medio
FROM clean_input
GROUP BY anno, regione, sigla_provincia, comune
ORDER BY anno, importo_totale DESC
