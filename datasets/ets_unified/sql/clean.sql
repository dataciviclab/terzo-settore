-- clean.sql — Fatti ETS (long format)
-- Driver-first: RUNTS 150k CF → join filtrato con 8 fonti Lab.
-- Output: una riga per (CF, fonte, anno, importo, dettagli)
-- Fonti Lab lette da GCS via https_url (bucket pubblico dataciviclab-clean).

WITH
-- ── 1. Driver: RUNTS (anagrafe ETS) ────────────────────────────────
runts_driver AS (
    SELECT DISTINCT TRIM(UPPER(codice_fiscale)) as cf
    FROM raw_input
),

-- ── 2. Fonti Lab da GCS ───────────────────────────────────────────

cinque AS (
    SELECT TRIM(REPLACE(codice_fiscale, chr(39), '')) as cf, anno,
           importo_totale_erogabile as importo
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
        'https://storage.googleapis.com/dataciviclab-clean/fts_eu_grants/2024/fts_eu_grants_2024_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/fts_eu_grants/2025/fts_eu_grants_2025_clean.parquet'
    ], union_by_name=true)
    WHERE TRIM(beneficiario_partita_iva) != '-'
),

rna AS (
    SELECT TRIM(REPLACE(codice_fiscale_beneficiario, chr(39), '')) as cf,
           anno, importo_nominale as importo
    FROM read_parquet([
        'https://storage.googleapis.com/dataciviclab-clean/rna_aiuti_stato/2024/rna_aiuti_stato_2024_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/rna_aiuti_stato/2025/rna_aiuti_stato_2025_clean.parquet'
    ], union_by_name=true)
),

pnrr AS (
    SELECT TRIM(cf_soggetto_attuatore) as cf, 2026 as anno, fin_totale as importo
    FROM 'https://storage.googleapis.com/dataciviclab-clean/pnrr_progetti/2026/pnrr_progetti_2026_clean.parquet'
),

bandi_gara AS (
    SELECT * FROM read_parquet([
        'https://storage.googleapis.com/dataciviclab-clean/anac_bandi_gara/2023/anac_bandi_gara_2023_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/anac_bandi_gara/2024/anac_bandi_gara_2024_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/anac_bandi_gara/2025/anac_bandi_gara_2025_clean.parquet'
    ], union_by_name=true)
),

anac AS (
    WITH tutti_partecipanti AS (
        SELECT cig, count(DISTINCT codice_fiscale) as n_part
        FROM 'https://storage.googleapis.com/dataciviclab-clean/anac_aggiudicatari/2026/anac_aggiudicatari_2026_clean.parquet'
        GROUP BY cig
    ),
    per_cig AS (
        SELECT a.codice_fiscale as cf, a.cig,
               MAX(ag.importo_aggiudicazione) / GREATEST(MAX(COALESCE(tp.n_part, 1)), 1) as importo,
               MAX(ag.data_aggiudicazione_definitiva) as data_max
        FROM 'https://storage.googleapis.com/dataciviclab-clean/anac_aggiudicatari/2026/anac_aggiudicatari_2026_clean.parquet' a
        JOIN 'https://storage.googleapis.com/dataciviclab-clean/anac_aggiudicazioni/2026/anac_aggiudicazioni_2026_clean.parquet' ag
          ON a.id_aggiudicazione = ag.id_aggiudicazione
        LEFT JOIN tutti_partecipanti tp ON a.cig = tp.cig
        WHERE a.codice_fiscale IS NOT NULL AND a.codice_fiscale != ''
          AND a.codice_fiscale IN (SELECT cf FROM runts_driver)
          AND ag.importo_aggiudicazione > 0
          AND ag.importo_aggiudicazione < 100000000000
          AND EXTRACT(YEAR FROM ag.data_aggiudicazione_definitiva) BETWEEN 2000 AND 2026
        GROUP BY a.codice_fiscale, a.cig
    )
    SELECT p.cf,
           EXTRACT(YEAR FROM p.data_max) as anno,
           p.importo,
           COALESCE(bg.oggetto_lotto, bg.oggetto_gara) as oggetto_gara,
           bg.denominazione_amministrazione_appaltante as stazione_appaltante,
           bg.TIPO_APPALTO_RISERVATO as appalto_riservato,
           bg.flag_pnrr
    FROM per_cig p
    LEFT JOIN bandi_gara bg ON p.cig = bg.cig
),

partecipanti AS (
    SELECT TRIM(codice_fiscale) as cf, count(DISTINCT cig) as n_gare
    FROM 'https://storage.googleapis.com/dataciviclab-clean/anac_partecipanti/2026/anac_partecipanti_2026_clean.parquet'
    WHERE codice_fiscale IS NOT NULL AND codice_fiscale != ''
      AND codice_fiscale IN (SELECT cf FROM runts_driver)
      AND tipo_soggetto NOT ILIKE '%STAZIONE APPALTANTE%'
    GROUP BY TRIM(codice_fiscale)
),

subappalti AS (
    SELECT cf_subappaltante as cf,
           EXTRACT(YEAR FROM data_autorizzazione) as anno,
           0 as importo
    FROM 'https://storage.googleapis.com/dataciviclab-clean/anac_subappalti/2026/anac_subappalti_2026_clean.parquet'
    WHERE cf_subappaltante IS NOT NULL AND cf_subappaltante != ''
      AND cf_subappaltante IN (SELECT cf FROM runts_driver)
      AND EXTRACT(YEAR FROM data_autorizzazione) BETWEEN 2000 AND 2026
),

patrimonio AS (
    SELECT REPLACE(REPLACE(soggetto_ricevente_cf, '[', ''), ']', '') as cf,
           anno, COALESCE(canone_annuale, 0) as importo
    FROM 'https://storage.googleapis.com/dataciviclab-clean/mef_patrimonio_detenzioni/2023/mef_patrimonio_detenzioni_2023_clean.parquet'
    WHERE soggetto_ricevente_cf IS NOT NULL AND soggetto_ricevente_cf != ''
      AND anno BETWEEN 2000 AND 2026
)

-- ── 3. Output: long format (una riga per CF/fonte/anno) ─────────────
SELECT '5x1000' as fonte, cf, anno, importo, NULL as oggetto_gara, NULL as stazione_appaltante, NULL as appalto_riservato, NULL as flag_pnrr FROM cinque WHERE cf IN (SELECT cf FROM runts_driver)
UNION ALL SELECT 'partecipazione', cf, 2026, n_gare, NULL, NULL, NULL, NULL FROM partecipanti WHERE cf IN (SELECT cf FROM runts_driver)
UNION ALL SELECT 'grant_ue', cf, anno, importo, NULL, NULL, NULL, NULL FROM fts WHERE cf IN (SELECT cf FROM runts_driver)
UNION ALL SELECT 'aiuto_stato', cf, anno, importo, NULL, NULL, NULL, NULL FROM rna WHERE cf IN (SELECT cf FROM runts_driver)
UNION ALL SELECT 'pnrr', cf, anno, importo, NULL, NULL, NULL, NULL FROM pnrr WHERE cf IN (SELECT cf FROM runts_driver)
UNION ALL SELECT 'anac', cf, anno, importo, oggetto_gara, stazione_appaltante, appalto_riservato, flag_pnrr FROM anac WHERE cf IN (SELECT cf FROM runts_driver)
UNION ALL SELECT 'subappalto', cf, anno, importo, NULL, NULL, NULL, NULL FROM subappalti WHERE cf IN (SELECT cf FROM runts_driver)
UNION ALL SELECT 'patrimonio', cf, anno, importo, NULL, NULL, NULL, NULL FROM patrimonio WHERE cf IN (SELECT cf FROM runts_driver)
