-- build_unified_ets.sql
-- Hub: RUNTS (anagrafe ETS) + join 5x1000, FTS, RNA, PNRR su codice_fiscale
-- Legge da GCS (no cache locale) + file locali (RUNTS, OC)
-- Output: una riga per ETS con tutti gli indicatori di capacità

COPY (
WITH runts AS (
    SELECT 
        codice_fiscale,
        denominazione,
        sezione,
        comune,
        provincia,
        flag_5x1000 as runts_flag_5x1000,
        data_iscrizione
    FROM read_parquet('data/runts_iscritti.parquet', union_by_name=true)
),

cinque AS (
    SELECT 
        TRIM(REPLACE(codice_fiscale, '''', '')) as cf,
        anno,
        importo_totale_erogabile,
        flag_ets_onlus,
        flag_asd,
        flag_ricerca_scientifica,
        flag_ricerca_sanitaria
    FROM read_parquet([
        'https://storage.googleapis.com/dataciviclab-clean/ade_cinque_per_mille/2023/ade_cinque_per_mille_2023_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/ade_cinque_per_mille/2024/ade_cinque_per_mille_2024_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/ade_cinque_per_mille/2025/ade_cinque_per_mille_2025_clean.parquet'
    ], union_by_name=true)
    WHERE flag_ets_onlus = true
),

cinque_agg AS (
    SELECT 
        cf,
        COUNT(*) as cinque_anni,
        SUM(importo_totale_erogabile) as cinque_totale,
        MAX(CASE WHEN anno = 2025 THEN importo_totale_erogabile END) as cinque_2025,
        MAX(flag_asd) as flag_asd,
        MAX(flag_ricerca_scientifica) as flag_ricerca_scientifica,
        MAX(flag_ricerca_sanitaria) as flag_ricerca_sanitaria
    FROM cinque
    GROUP BY cf
),

fts AS (
    SELECT 
        CASE 
            WHEN TRIM(beneficiario_partita_iva) = '-' THEN NULL
            WHEN upper(TRIM(beneficiario_partita_iva)) LIKE 'IT%' 
                THEN SUBSTRING(TRIM(beneficiario_partita_iva), 3)
            ELSE TRIM(beneficiario_partita_iva)
        END as cf,
        COUNT(*) as grant_ue_progetti,
        SUM(importo_contrattato) as grant_ue_totale,
        MAX(flag_no_profit) as flag_no_profit,
        MAX(flag_ong) as flag_ong
    FROM read_parquet([
        'https://storage.googleapis.com/dataciviclab-clean/fts_eu_grants/2020/fts_eu_grants_2020_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/fts_eu_grants/2021/fts_eu_grants_2021_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/fts_eu_grants/2022/fts_eu_grants_2022_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/fts_eu_grants/2023/fts_eu_grants_2023_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/fts_eu_grants/2024/fts_eu_grants_2024_clean.parquet'
    ], union_by_name=true)
    WHERE TRIM(beneficiario_partita_iva) != '-'
    GROUP BY cf
),

rna AS (
    SELECT 
        TRIM(REPLACE(codice_fiscale_beneficiario, '''', '')) as cf,
        COUNT(*) as aiuti_stato_progetti,
        SUM(importo_nominale) as aiuti_stato_totale
    FROM read_parquet([
        'https://storage.googleapis.com/dataciviclab-clean/rna_aiuti_stato/2025/rna_aiuti_stato_2025_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/rna_aiuti_stato/2026/rna_aiuti_stato_2026_clean.parquet'
    ], union_by_name=true)
    GROUP BY TRIM(REPLACE(codice_fiscale_beneficiario, '''', ''))
),

pnrr AS (
    SELECT 
        TRIM(cf_soggetto_attuatore) as cf,
        COUNT(*) as pnrr_progetti,
        SUM(fin_totale) as pnrr_totale
    FROM read_parquet('https://storage.googleapis.com/dataciviclab-clean/pnrr_progetti/2026/pnrr_progetti_2026_clean.parquet', union_by_name=true)
    GROUP BY TRIM(cf_soggetto_attuatore)
),

anac AS (
    SELECT a.codice_fiscale as cf,
           ROUND(SUM(ag.importo_aggiudicazione), 0) as importo_appalti
    FROM read_parquet('https://storage.googleapis.com/dataciviclab-clean/anac_aggiudicatari/2026/anac_aggiudicatari_2026_clean.parquet', union_by_name=true) a
    JOIN read_parquet('https://storage.googleapis.com/dataciviclab-clean/anac_aggiudicazioni/2026/anac_aggiudicazioni_2026_clean.parquet', union_by_name=true) ag
      ON a.cig = ag.cig
    WHERE ag.importo_aggiudicazione > 0
      AND ag.importo_aggiudicazione < 100000000000
      AND EXTRACT(YEAR FROM ag.data_aggiudicazione_definitiva) BETWEEN 2000 AND 2026
      AND a.codice_fiscale IS NOT NULL AND a.codice_fiscale != ''
    GROUP BY a.codice_fiscale
)

SELECT 
    r.codice_fiscale,
    r.denominazione,
    r.sezione,
    r.comune,
    r.provincia,
    r.runts_flag_5x1000,
    r.data_iscrizione,

    -- 5x1000
    CASE WHEN c.cinque_2025 IS NOT NULL THEN TRUE ELSE FALSE END as ha_5x1000,
    c.cinque_2025 as cinque_2025,
    c.cinque_totale as cinque_totale,
    c.cinque_anni as cinque_anni,
    COALESCE(c.flag_asd, FALSE) as flag_asd,
    COALESCE(c.flag_ricerca_scientifica, FALSE) as flag_ricerca_scientifica,
    COALESCE(c.flag_ricerca_sanitaria, FALSE) as flag_ricerca_sanitaria,
    regexp_matches(lower(r.denominazione), '(asd|associazione sportiva|società sportiva|sportiva dilettantistica|polisportiva)') as flag_sport_denom,
    -- oc_* rimosso: Open Cooperazione non più mantenuto

    -- Grant UE
    CASE WHEN f.grant_ue_totale > 0 THEN TRUE ELSE FALSE END as ha_grant_ue,
    f.grant_ue_progetti,
    f.grant_ue_totale,
    COALESCE(f.flag_no_profit = 'true', FALSE) as flag_ue_no_profit,
    COALESCE(f.flag_ong = 'true', FALSE) as flag_ue_ong,

    -- Aiuti di Stato
    CASE WHEN rna.aiuti_stato_totale > 0 THEN TRUE ELSE FALSE END as ha_aiuti_stato,
    rna.aiuti_stato_progetti,
    rna.aiuti_stato_totale,

    -- PNRR
    CASE WHEN pnrr.pnrr_totale > 0 THEN TRUE ELSE FALSE END as ha_pnrr,
    pnrr.pnrr_progetti,
    pnrr.pnrr_totale,

    -- Appalti pubblici ANAC
    CASE WHEN COALESCE(anac.importo_appalti, 0) > 0 THEN TRUE ELSE FALSE END as ha_appalti,
    COALESCE(anac.importo_appalti, 0) as importo_appalti,

    -- Indicatore composito di capacità
    -- Alta: grant UE (progetti europei finanziati)
    -- Medio-alta: aiuti stato o PNRR (progetti co-finanziati)
    -- Media: 5x1000 pluriennale (>=3 anni) o singolo >10k
    -- Base: 5x1000 (almeno una donazione) o Impresa Sociale (per statuto)
    CASE 
        WHEN COALESCE(f.grant_ue_totale, 0) > 0 THEN 'alta'
        WHEN COALESCE(rna.aiuti_stato_totale, 0) > 0 THEN 'medio-alta'
        WHEN COALESCE(pnrr.pnrr_totale, 0) > 0 THEN 'medio-alta'
        WHEN COALESCE(c.cinque_2025, 0) > 10000 THEN 'media'
        WHEN COALESCE(c.cinque_anni, 0) >= 3 AND COALESCE(c.cinque_2025, 0) > 0 THEN 'media'
        WHEN COALESCE(c.cinque_2025, 0) > 0 THEN 'base'
        WHEN r.sezione = 'IMPRESE SOCIALI' THEN 'base'
        ELSE 'sconosciuta'
    END as capacita_progettuale

FROM runts r
LEFT JOIN cinque_agg c ON r.codice_fiscale = c.cf
LEFT JOIN fts f ON r.codice_fiscale = f.cf
LEFT JOIN rna ON r.codice_fiscale = rna.cf
LEFT JOIN pnrr ON r.codice_fiscale = pnrr.cf
LEFT JOIN anac ON r.codice_fiscale = anac.cf
ORDER BY r.provincia, r.comune, r.denominazione)
TO 'data/unified_ets.parquet' (FORMAT PARQUET);
