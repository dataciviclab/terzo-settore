-- mart_per_categoria.sql — 5x1000 per categoria x anno
-- Grain: categoria (flag) x anno
-- Output: quanti enti per tipo, importo, evoluzione

SELECT
    anno,
    'ETS/ONLUS' AS categoria, COUNT(DISTINCT codice_fiscale) AS enti, ROUND(SUM(importo_totale_erogabile)::NUMERIC, 0) AS importo
FROM clean_input WHERE flag_ets_onlus GROUP BY anno
UNION ALL
SELECT anno, 'ASD', COUNT(DISTINCT codice_fiscale), ROUND(SUM(importo_totale_erogabile)::NUMERIC, 0)
FROM clean_input WHERE flag_asd GROUP BY anno
UNION ALL
SELECT anno, 'Ricerca scientifica', COUNT(DISTINCT codice_fiscale), ROUND(SUM(importo_totale_erogabile)::NUMERIC, 0)
FROM clean_input WHERE flag_ricerca_scientifica GROUP BY anno
UNION ALL
SELECT anno, 'Ricerca sanitaria', COUNT(DISTINCT codice_fiscale), ROUND(SUM(importo_totale_erogabile)::NUMERIC, 0)
FROM clean_input WHERE flag_ricerca_sanitaria GROUP BY anno
UNION ALL
SELECT anno, 'Comuni', COUNT(DISTINCT codice_fiscale), ROUND(SUM(importo_totale_erogabile)::NUMERIC, 0)
FROM clean_input WHERE flag_comune GROUP BY anno
UNION ALL
SELECT anno, 'Beni culturali', COUNT(DISTINCT codice_fiscale), ROUND(SUM(importo_totale_erogabile)::NUMERIC, 0)
FROM clean_input WHERE flag_beni_culturali GROUP BY anno
UNION ALL
SELECT anno, 'Aree protette', COUNT(DISTINCT codice_fiscale), ROUND(SUM(importo_totale_erogabile)::NUMERIC, 0)
FROM clean_input WHERE flag_area_protetta GROUP BY anno
ORDER BY anno, importo DESC
