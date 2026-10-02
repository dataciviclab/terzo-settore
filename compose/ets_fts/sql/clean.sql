-- clean.sql — Compose RUNTS + FTS (Grant UE)
WITH
anagrafe AS (
    SELECT codice_fiscale
    FROM raw_input
    WHERE codice_fiscale IS NOT NULL
      AND trim(codice_fiscale) != ''
),
fts AS (
    SELECT CASE
        WHEN TRIM(beneficiario_partita_iva) = '-' THEN NULL
        WHEN upper(TRIM(beneficiario_partita_iva)) LIKE 'IT%' THEN SUBSTRING(TRIM(beneficiario_partita_iva), 3)
        ELSE TRIM(beneficiario_partita_iva)
    END as codice_fiscale, anno, importo_contrattato as importo,
    nome_programma, flag_no_profit, flag_ong
    FROM read_parquet({support.fts_eu_grants.clean}, union_by_name=true)
    WHERE TRIM(beneficiario_partita_iva) != '-'
)
SELECT
    a.codice_fiscale,
    'grant_ue' as fonte,
    f.anno,
    f.importo,
    f.nome_programma,
    f.flag_no_profit,
    f.flag_ong
FROM anagrafe a
JOIN fts f ON a.codice_fiscale = f.codice_fiscale
