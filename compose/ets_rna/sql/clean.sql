-- clean.sql — Compose RUNTS + RNA
WITH
anagrafe AS (
    SELECT codice_fiscale
    FROM raw_input
    WHERE codice_fiscale IS NOT NULL
      AND trim(codice_fiscale) != ''
),
rna AS (
    SELECT TRIM(REPLACE(codice_fiscale_beneficiario, chr(39), '')) as codice_fiscale,
           anno, importo_nominale as importo,
           soggetto_concedente, procedimento, titolo_misura
    FROM read_parquet({support.rna_aiuti_stato.clean}, union_by_name=true)
)
SELECT
    a.codice_fiscale,
    'aiuto_stato' as fonte,
    r.anno,
    r.importo,
    r.soggetto_concedente,
    r.procedimento,
    r.titolo_misura
FROM anagrafe a
JOIN rna r ON a.codice_fiscale = r.codice_fiscale
