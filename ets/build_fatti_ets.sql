-- build_fatti_ets.sql
-- Tabella long: una riga per (ETS, fonte, anno, importo)
-- Fonti: 5x1000, grant_ue, aiuto_stato, pnrr, anac

COPY (
WITH cinque AS (
    SELECT TRIM(REPLACE(codice_fiscale, chr(39), '')) as cf, anno, importo_totale_erogabile as importo
    FROM read_parquet([
        'https://storage.googleapis.com/dataciviclab-clean/ade_cinque_per_mille/2023/ade_cinque_per_mille_2023_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/ade_cinque_per_mille/2024/ade_cinque_per_mille_2024_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/ade_cinque_per_mille/2025/ade_cinque_per_mille_2025_clean.parquet'
    ], union_by_name=true)
    WHERE flag_ets_onlus = true
),
fts AS (
    SELECT CASE
        WHEN TRIM(beneficiario_partita_iva) = '-' THEN NULL
        WHEN upper(TRIM(beneficiario_partita_iva)) LIKE 'IT%' THEN SUBSTRING(TRIM(beneficiario_partita_iva), 3)
        ELSE TRIM(beneficiario_partita_iva)
    END as cf, anno, importo_contrattato as importo
    FROM read_parquet([
        'https://storage.googleapis.com/dataciviclab-clean/fts_eu_grants/2020/fts_eu_grants_2020_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/fts_eu_grants/2021/fts_eu_grants_2021_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/fts_eu_grants/2022/fts_eu_grants_2022_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/fts_eu_grants/2023/fts_eu_grants_2023_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/fts_eu_grants/2024/fts_eu_grants_2024_clean.parquet'
    ], union_by_name=true)
    WHERE TRIM(beneficiario_partita_iva) != '-'
),
rna AS (
    SELECT TRIM(REPLACE(codice_fiscale_beneficiario, chr(39), '')) as cf, anno, importo_nominale as importo
    FROM read_parquet([
        'https://storage.googleapis.com/dataciviclab-clean/rna_aiuti_stato/2025/rna_aiuti_stato_2025_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/rna_aiuti_stato/2026/rna_aiuti_stato_2026_clean.parquet'
    ], union_by_name=true)
),
pnrr AS (
    SELECT TRIM(cf_soggetto_attuatore) as cf, 2026 as anno, fin_totale as importo
    FROM read_parquet('https://storage.googleapis.com/dataciviclab-clean/pnrr_progetti/2026/pnrr_progetti_2026_clean.parquet', union_by_name=true)
),
bandi_gara AS (
    SELECT * FROM read_parquet([
        'https://storage.googleapis.com/dataciviclab-clean/anac_bandi_gara/2023/anac_bandi_gara_2023_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/anac_bandi_gara/2024/anac_bandi_gara_2024_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/anac_bandi_gara/2025/anac_bandi_gara_2025_clean.parquet'
    ], union_by_name=true)
),
anac AS (
    SELECT a.codice_fiscale as cf,
           EXTRACT(YEAR FROM ag.data_aggiudicazione_definitiva) as anno,
           ag.importo_aggiudicazione as importo,
           COALESCE(bg.oggetto_lotto, bg.oggetto_gara) as oggetto_gara,
           bg.denominazione_amministrazione_appaltante as stazione_appaltante,
           bg.TIPO_APPALTO_RISERVATO as appalto_riservato,
           bg.flag_pnrr
    FROM read_parquet('https://storage.googleapis.com/dataciviclab-clean/anac_aggiudicatari/2026/anac_aggiudicatari_2026_clean.parquet', union_by_name=true) a
    JOIN read_parquet('https://storage.googleapis.com/dataciviclab-clean/anac_aggiudicazioni/2026/anac_aggiudicazioni_2026_clean.parquet', union_by_name=true) ag
      ON a.cig = ag.cig
    LEFT JOIN bandi_gara bg ON a.cig = bg.cig
    WHERE a.codice_fiscale IS NOT NULL AND a.codice_fiscale != ''
      AND ag.importo_aggiudicazione > 0
      AND ag.importo_aggiudicazione < 100000000000
      AND EXTRACT(YEAR FROM ag.data_aggiudicazione_definitiva) BETWEEN 2000 AND 2026
)
SELECT '5x1000' as fonte, cf, anno, importo, NULL as oggetto_gara, NULL as stazione_appaltante, NULL as appalto_riservato, NULL as flag_pnrr FROM cinque WHERE cf IS NOT NULL
UNION ALL
SELECT 'grant_ue', cf, anno, importo, NULL, NULL, NULL, NULL FROM fts WHERE cf IS NOT NULL
UNION ALL
SELECT 'aiuto_stato', cf, anno, importo, NULL, NULL, NULL, NULL FROM rna WHERE cf IS NOT NULL
UNION ALL
SELECT 'pnrr', cf, anno, importo, NULL, NULL, NULL, NULL FROM pnrr WHERE cf IS NOT NULL
UNION ALL
SELECT 'anac', cf, anno, importo, oggetto_gara, stazione_appaltante, appalto_riservato, flag_pnrr FROM anac WHERE cf IS NOT NULL
)
TO 'data/fatti_ets.parquet' (FORMAT PARQUET);
