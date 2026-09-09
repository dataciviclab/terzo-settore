-- clean.sql — Compose RUNTS + 5x1000 (ADE)
-- Output: una riga per CF con donazioni 5 per mille

WITH
anagrafe AS (
    SELECT codice_fiscale, denominazione, sezione, comune, provincia
    FROM raw_input
    WHERE codice_fiscale IS NOT NULL
      AND trim(codice_fiscale) != ''
),

cinque AS (
    SELECT TRIM(REPLACE(codice_fiscale, chr(39), '')) as codice_fiscale, anno,
           importo_totale_erogabile as importo,
           flag_asd, flag_ricerca_scientifica, flag_ricerca_sanitaria,
           flag_comune, flag_beni_culturali, flag_area_protetta
    FROM read_parquet([
        'https://storage.googleapis.com/dataciviclab-clean/ade_cinque_per_mille/2023/ade_cinque_per_mille_2023_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/ade_cinque_per_mille/2024/ade_cinque_per_mille_2024_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/ade_cinque_per_mille/2025/ade_cinque_per_mille_2025_clean.parquet'
    ], union_by_name=true)
    WHERE flag_ets_onlus = true
)

SELECT
    a.codice_fiscale,
    a.denominazione,
    a.sezione,
    a.comune,
    a.provincia,
    '5x1000' as fonte,
    c.anno,
    c.importo,
    c.flag_asd, c.flag_ricerca_scientifica, c.flag_ricerca_sanitaria,
    c.flag_comune, c.flag_beni_culturali, c.flag_area_protetta
FROM anagrafe a
JOIN cinque c ON a.codice_fiscale = c.codice_fiscale
