-- clean.sql — Compose RUNTS + MEF (Patrimonio)
WITH
anagrafe AS (
    SELECT codice_fiscale
    FROM raw_input
    WHERE codice_fiscale IS NOT NULL
      AND trim(codice_fiscale) != ''
),
mef AS (
    SELECT REPLACE(REPLACE(soggetto_ricevente_cf, '[', ''), ']', '') as codice_fiscale,
           anno, COALESCE(canone_annuale, 0) as importo,
           finalita_pf, tipologia_bene
    FROM 'https://storage.googleapis.com/dataciviclab-clean/mef_patrimonio_detenzioni/2023/mef_patrimonio_detenzioni_2023_clean.parquet'
    WHERE soggetto_ricevente_cf IS NOT NULL AND soggetto_ricevente_cf != ''
      AND anno BETWEEN 2000 AND 2026
)
SELECT
    a.codice_fiscale,
    'patrimonio' as fonte,
    m.anno,
    m.importo,
    m.finalita_pf,
    m.tipologia_bene
FROM anagrafe a
JOIN mef m ON a.codice_fiscale = m.codice_fiscale
