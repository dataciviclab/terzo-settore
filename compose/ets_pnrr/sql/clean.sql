-- clean.sql — Compose RUNTS + PNRR
WITH
anagrafe AS (
    SELECT codice_fiscale
    FROM raw_input
    WHERE codice_fiscale IS NOT NULL
      AND trim(codice_fiscale) != ''
),
pnrr AS (
    SELECT TRIM(cf_soggetto_attuatore) as codice_fiscale, 2026 as anno, fin_totale as importo,
           programma, missione, descrizione_missione
    FROM 'https://storage.googleapis.com/dataciviclab-clean/pnrr_progetti/2026/pnrr_progetti_2026_clean.parquet'
    WHERE cf_soggetto_attuatore IS NOT NULL AND TRIM(cf_soggetto_attuatore) != ''
)
SELECT
    a.codice_fiscale,
    'pnrr' as fonte,
    p.anno,
    p.importo,
    p.programma,
    p.missione,
    p.descrizione_missione
FROM anagrafe a
JOIN pnrr p ON a.codice_fiscale = p.codice_fiscale
