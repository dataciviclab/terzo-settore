-- mart_top_enti.sql — Top enti per importo 5x1000
-- Grain: ente x anno
-- Output: top enti con tutti i flag e importi

SELECT
    anno,
    codice_fiscale,
    denominazione,
    regione,
    sigla_provincia,
    comune,
    flag_ets_onlus,
    flag_asd,
    flag_ricerca_scientifica,
    flag_ricerca_sanitaria,
    flag_comune,
    flag_beni_culturali,
    flag_area_protetta,
    numero_scelte,
    importo_totale_erogabile,
    ROUND(importo_totale_erogabile::NUMERIC, 0) AS importo,
    RANK() OVER (PARTITION BY anno ORDER BY importo_totale_erogabile DESC) AS ranking
FROM clean_input
QUALIFY ranking <= 100
ORDER BY anno, ranking
