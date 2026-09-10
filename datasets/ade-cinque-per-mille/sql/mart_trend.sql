-- mart_trend.sql — Trend annuale 5x1000
-- Grain: anno
-- Output: enti totali, per flag, importi, variazione %, CAGR

WITH base AS (
    SELECT
        anno,
        COUNT(DISTINCT codice_fiscale) AS enti_totali,
        COUNT(DISTINCT CASE WHEN flag_ets_onlus THEN codice_fiscale END) AS enti_ets,
        COUNT(DISTINCT CASE WHEN flag_asd THEN codice_fiscale END) AS enti_asd,
        COUNT(DISTINCT CASE WHEN flag_ricerca_scientifica OR flag_ricerca_sanitaria THEN codice_fiscale END) AS enti_ricerca,
        COUNT(DISTINCT CASE WHEN flag_beni_culturali THEN codice_fiscale END) AS enti_cultura,
        COUNT(DISTINCT CASE WHEN flag_comune THEN codice_fiscale END) AS enti_comuni,
        ROUND(SUM(importo_totale_erogabile)::NUMERIC, 0) AS importo_totale,
        ROUND(AVG(importo_totale_erogabile)::NUMERIC, 0) AS importo_medio,
        ROUND(MEDIAN(importo_totale_erogabile)::NUMERIC, 0) AS importo_mediano,
        COUNT(DISTINCT regione) AS regioni
    FROM clean_input
    GROUP BY anno
),
con_lag AS (
    SELECT
        *,
        LAG(enti_totali) OVER (ORDER BY anno) AS enti_prev,
        LAG(importo_totale) OVER (ORDER BY anno) AS importo_prev
    FROM base
)
SELECT
    anno,
    enti_totali,
    enti_ets,
    enti_asd,
    enti_ricerca,
    enti_cultura,
    enti_comuni,
    importo_totale,
    importo_medio,
    importo_mediano,
    regioni,
    CASE WHEN enti_prev > 0 THEN ROUND(((enti_totali - enti_prev)::NUMERIC / enti_prev * 100), 1) END AS var_enti_pct,
    CASE WHEN importo_prev > 0 THEN ROUND(((importo_totale - importo_prev)::NUMERIC / importo_prev * 100), 1) END AS var_importo_pct
FROM con_lag
ORDER BY anno
