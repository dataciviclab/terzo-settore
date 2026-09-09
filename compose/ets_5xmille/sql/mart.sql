-- mart.sql — ETS + 5x1000: profilo donazioni per mille
-- Output: una riga per ETS con info 5x1000 + flag tematici

SELECT
    codice_fiscale,
    denominazione,
    sezione,
    comune,
    provincia,
    COUNT(*) as anni,
    ROUND(SUM(importo), 0) as importo_totale,
    MAX(CASE WHEN anno = 2025 THEN importo END) as importo_2025,
    MAX(flag_asd) as flag_asd,
    MAX(flag_ricerca_scientifica) as flag_ricerca_scientifica,
    MAX(flag_ricerca_sanitaria) as flag_ricerca_sanitaria,
    MAX(flag_comune) as flag_comune,
    MAX(flag_beni_culturali) as flag_beni_culturali,
    MAX(flag_area_protetta) as flag_area_protetta
FROM clean_input
GROUP BY codice_fiscale, denominazione, sezione, comune, provincia
ORDER BY importo_totale DESC
