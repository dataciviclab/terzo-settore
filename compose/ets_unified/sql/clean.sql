-- clean.sql — Fatti ETS (long format)
-- Legge i clean parquet prodotti dai compose locali.
-- Output: una riga per (CF, fonte, anno, importo).

WITH
-- ── Driver: RUNTS (anagrafe ETS) ──────────────────────────────────
runts_driver AS (
    SELECT DISTINCT TRIM(UPPER(codice_fiscale)) as cf
    FROM raw_input
),

-- ── Lettura clean locali dei compose ───────────────────────────────

cinque AS (
    SELECT codice_fiscale, '5x1000' as fonte, anno, importo
    FROM '{support.ets_5xmille.clean}'
),

anac_agg AS (
    SELECT codice_fiscale, fonte, anno, importo
    FROM '{support.ets_anac.clean}'
    WHERE fonte = 'anac_aggiudicazione'
),

anac_part AS (
    SELECT codice_fiscale, 'partecipazione' as fonte, 2026 as anno, n_gare as importo
    FROM '{support.ets_anac.clean}'
    WHERE fonte = 'anac_partecipazione'
),

anac_sub AS (
    SELECT codice_fiscale, 'subappalto' as fonte, anno, importo
    FROM '{support.ets_anac.clean}'
    WHERE fonte = 'anac_subappalto'
),

fts AS (
    SELECT codice_fiscale, 'grant_ue' as fonte, anno, importo
    FROM '{support.ets_fts.clean}'
),

rna AS (
    SELECT codice_fiscale, 'aiuto_stato' as fonte, anno, importo
    FROM '{support.ets_rna.clean}'
),

pnrr AS (
    SELECT codice_fiscale, 'pnrr' as fonte, anno, importo
    FROM '{support.ets_pnrr.clean}'
),

mef AS (
    SELECT codice_fiscale, 'patrimonio' as fonte, anno, importo
    FROM '{support.ets_mef.clean}'
)

-- ── Output: long format (una riga per CF/fonte/anno) ─────────────
SELECT codice_fiscale as cf, fonte, anno, importo FROM cinque WHERE codice_fiscale IN (SELECT cf FROM runts_driver)
UNION ALL SELECT codice_fiscale, fonte, anno, importo FROM anac_agg WHERE codice_fiscale IN (SELECT cf FROM runts_driver)
UNION ALL SELECT codice_fiscale, fonte, anno, importo FROM anac_part WHERE codice_fiscale IN (SELECT cf FROM runts_driver)
UNION ALL SELECT codice_fiscale, fonte, anno, importo FROM anac_sub WHERE codice_fiscale IN (SELECT cf FROM runts_driver)
UNION ALL SELECT codice_fiscale, fonte, anno, importo FROM fts WHERE codice_fiscale IN (SELECT cf FROM runts_driver)
UNION ALL SELECT codice_fiscale, fonte, anno, importo FROM rna WHERE codice_fiscale IN (SELECT cf FROM runts_driver)
UNION ALL SELECT codice_fiscale, fonte, anno, importo FROM pnrr WHERE codice_fiscale IN (SELECT cf FROM runts_driver)
UNION ALL SELECT codice_fiscale, fonte, anno, importo FROM mef WHERE codice_fiscale IN (SELECT cf FROM runts_driver)
