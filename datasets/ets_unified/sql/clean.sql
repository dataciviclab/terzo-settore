-- clean.sql — Profilo ETS unificato
-- Combina driver-first (RUNTS × fonti Lab) + PIVOT + geografia.
-- Fonti Lab lette da GCS via https_url (bucket pubblico dataciviclab-clean).
-- RUNTS letto dal support intra-repo (datasets/runts).

WITH
-- ── 1. Driver: RUNTS (anagrafe ETS) ────────────────────────────────
runts_driver AS (
    SELECT DISTINCT TRIM(UPPER(codice_fiscale)) as cf
    FROM read_parquet('{support.runts.clean}')
),

anagrafe AS (
    SELECT codice_fiscale, denominazione, sezione, comune, provincia, data_iscrizione
    FROM read_parquet('{support.runts.clean}')
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
        'https://storage.googleapis.com/dataciviclab-clean/fts_eu_grants/2024/fts_eu_grants_2024_clean.parquet'
    ], union_by_name=true)
    WHERE TRIM(beneficiario_partita_iva) != '-'
),

rna AS (
    SELECT TRIM(REPLACE(codice_fiscale_beneficiario, chr(39), '')) as cf,
           anno, importo_nominale as importo
    FROM read_parquet([
        'https://storage.googleapis.com/dataciviclab-clean/rna_aiuti_stato/2025/rna_aiuti_stato_2025_clean.parquet',
        'https://storage.googleapis.com/dataciviclab-clean/rna_aiuti_stato/2026/rna_aiuti_stato_2026_clean.parquet'
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
    WITH partecipanti_per_cig AS (
        SELECT cig, count(DISTINCT codice_fiscale) as n_part
        FROM 'https://storage.googleapis.com/dataciviclab-clean/anac_aggiudicatari/2026/anac_aggiudicatari_2026_clean.parquet'
        WHERE codice_fiscale IN (SELECT cf FROM runts_driver)
        GROUP BY cig
    ),
    per_cig AS (
        SELECT a.codice_fiscale as cf, a.cig,
               MAX(ag.importo_aggiudicazione) / GREATEST(MAX(COALESCE(p.n_part, 1)), 1) as importo,
               MAX(ag.data_aggiudicazione_definitiva) as data_max
        FROM 'https://storage.googleapis.com/dataciviclab-clean/anac_aggiudicatari/2026/anac_aggiudicatari_2026_clean.parquet' a
        JOIN 'https://storage.googleapis.com/dataciviclab-clean/anac_aggiudicazioni/2026/anac_aggiudicazioni_2026_clean.parquet' ag
          ON a.id_aggiudicazione = ag.id_aggiudicazione
        LEFT JOIN partecipanti_per_cig p ON a.cig = p.cig
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
),

-- ── 3. Fatti long (driver-first) ──────────────────────────────────
fatti_ets AS (
    SELECT '5x1000' as fonte, cf, anno, importo, NULL as oggetto_gara, NULL as stazione_appaltante, NULL as appalto_riservato, NULL as flag_pnrr FROM cinque WHERE cf IN (SELECT cf FROM runts_driver)
    UNION ALL SELECT 'partecipazione', cf, 2026, n_gare, NULL, NULL, NULL, NULL FROM partecipanti WHERE cf IN (SELECT cf FROM runts_driver)
    UNION ALL SELECT 'grant_ue', cf, anno, importo, NULL, NULL, NULL, NULL FROM fts WHERE cf IN (SELECT cf FROM runts_driver)
    UNION ALL SELECT 'aiuto_stato', cf, anno, importo, NULL, NULL, NULL, NULL FROM rna WHERE cf IN (SELECT cf FROM runts_driver)
    UNION ALL SELECT 'pnrr', cf, anno, importo, NULL, NULL, NULL, NULL FROM pnrr WHERE cf IN (SELECT cf FROM runts_driver)
    UNION ALL SELECT 'anac', cf, anno, importo, oggetto_gara, stazione_appaltante, appalto_riservato, flag_pnrr FROM anac WHERE cf IN (SELECT cf FROM runts_driver)
    UNION ALL SELECT 'subappalto', cf, anno, importo, NULL, NULL, NULL, NULL FROM subappalti WHERE cf IN (SELECT cf FROM runts_driver)
    UNION ALL SELECT 'patrimonio', cf, anno, importo, NULL, NULL, NULL, NULL FROM patrimonio WHERE cf IN (SELECT cf FROM runts_driver)
),

-- ── 4. PIVOT per ETS ──────────────────────────────────────────────
fatti_pivot AS (
    SELECT cf,
        COUNT(CASE WHEN fonte = '5x1000' THEN 1 END) as anni_5x1000,
        SUM(CASE WHEN fonte = '5x1000' THEN importo END) as importo_5x1000_totale,
        MAX(CASE WHEN fonte = '5x1000' AND anno = 2025 THEN importo END) as importo_5x1000_2025,
        COUNT(CASE WHEN fonte = 'grant_ue' THEN 1 END) as progetti_ue,
        SUM(CASE WHEN fonte = 'grant_ue' THEN importo END) as importo_ue,
        COUNT(CASE WHEN fonte = 'aiuto_stato' THEN 1 END) as progetti_aiuti_stato,
        SUM(CASE WHEN fonte = 'aiuto_stato' THEN importo END) as importo_aiuti_stato,
        COUNT(CASE WHEN fonte = 'pnrr' THEN 1 END) as progetti_pnrr,
        SUM(CASE WHEN fonte = 'pnrr' THEN importo END) as importo_pnrr,
        COUNT(CASE WHEN fonte = 'anac' THEN 1 END) as numero_appalti,
        SUM(CASE WHEN fonte = 'anac' THEN importo END) as importo_appalti,
        COUNT(CASE WHEN fonte = 'anac' AND appalto_riservato IS NOT NULL AND appalto_riservato != ''
                    AND appalto_riservato != 'LA PARTECIPAZIONE NON È RISERVATA.' THEN 1 END) as appalti_riservati,
        COUNT(CASE WHEN fonte = 'anac' AND flag_pnrr = true THEN 1 END) as appalti_pnrr,
        SUM(CASE WHEN fonte = 'partecipazione' THEN importo END) as gare_partecipate,
        COUNT(CASE WHEN fonte = 'subappalto' THEN 1 END) as subappalti,
        COUNT(CASE WHEN fonte = 'patrimonio' THEN 1 END) as patrimonio_immobili,
        SUM(CASE WHEN fonte = 'patrimonio' THEN importo END) as canone_totale
    FROM fatti_ets
    GROUP BY cf
),

-- ── 5. Geografia (comuni_master da GCS) ──────────────────────────
geo AS (
    SELECT lower(denominazione) as comune_norm, codice_istat, sigla_provincia,
           provincia as nome_provincia, regione
    FROM 'https://storage.googleapis.com/dataciviclab-clean/comuni_master/2026/comuni_master_2026_clean.parquet'
)

-- ── 6. Output: una riga per ETS ──────────────────────────────────
SELECT
    a.codice_fiscale,
    a.denominazione,
    a.sezione,
    a.comune,
    cm.codice_istat,
    COALESCE(cm.sigla_provincia, a.provincia) as provincia,
    cm.regione,
    a.data_iscrizione,

    CASE WHEN COALESCE(importo_5x1000_2025, 0) > 0 THEN TRUE ELSE FALSE END as ha_5x1000,
    importo_5x1000_2025,
    COALESCE(importo_5x1000_totale, 0) as importo_5x1000_totale,
    COALESCE(anni_5x1000, 0) as anni_5x1000,
    regexp_matches(lower(a.denominazione), '(asd|associazione sportiva|società sportiva|sportiva dilettantistica|polisportiva)') as ha_sport_in_denominazione,

    CASE WHEN COALESCE(importo_ue, 0) > 0 THEN TRUE ELSE FALSE END as ha_finanziamenti_ue,
    COALESCE(progetti_ue, 0) as progetti_ue,
    COALESCE(importo_ue, 0) as importo_ue,

    CASE WHEN COALESCE(importo_aiuti_stato, 0) > 0 THEN TRUE ELSE FALSE END as ha_aiuti_stato,
    COALESCE(progetti_aiuti_stato, 0) as progetti_aiuti_stato,
    COALESCE(importo_aiuti_stato, 0) as importo_aiuti_stato,

    CASE WHEN COALESCE(importo_pnrr, 0) > 0 THEN TRUE ELSE FALSE END as ha_progetti_pnrr,
    COALESCE(progetti_pnrr, 0) as progetti_pnrr,
    COALESCE(importo_pnrr, 0) as importo_pnrr,

    CASE WHEN COALESCE(importo_appalti, 0) > 0 THEN TRUE ELSE FALSE END as ha_appalti_pubblici,
    COALESCE(numero_appalti, 0) as numero_appalti,
    COALESCE(importo_appalti, 0) as importo_appalti,
    COALESCE(appalti_riservati, 0) as appalti_riservati,
    COALESCE(appalti_pnrr, 0) as appalti_pnrr,
    COALESCE(subappalti, 0) as subappalti,
    COALESCE(patrimonio_immobili, 0) as patrimonio_immobili,
    COALESCE(canone_totale, 0) as canone_totale,

    CASE WHEN COALESCE(gare_partecipate, 0) > 0 THEN TRUE ELSE FALSE END as ha_partecipato_gare,
    COALESCE(gare_partecipate, 0) as gare_partecipate,

    CASE
        WHEN COALESCE(importo_ue, 0) > 0 THEN 'alta'
        WHEN COALESCE(numero_appalti, 0) >= 10 THEN 'alta'
        WHEN COALESCE(appalti_riservati, 0) >= 3 THEN 'alta'
        WHEN COALESCE(importo_aiuti_stato, 0) > 0 THEN 'medio-alta'
        WHEN COALESCE(importo_pnrr, 0) > 0 THEN 'medio-alta'
        WHEN COALESCE(numero_appalti, 0) >= 3 THEN 'medio-alta'
        WHEN COALESCE(importo_5x1000_2025, 0) > 10000 THEN 'media'
        WHEN COALESCE(anni_5x1000, 0) >= 3 AND COALESCE(importo_5x1000_2025, 0) > 0 THEN 'media'
        WHEN COALESCE(numero_appalti, 0) >= 1 THEN 'media'
        WHEN COALESCE(importo_5x1000_2025, 0) > 0 THEN 'base'
        WHEN a.sezione = 'IMPRESI SOCIALI' THEN 'base'
        ELSE 'sconosciuta'
    END as capacita_progettuale

FROM anagrafe a
LEFT JOIN fatti_pivot f ON a.codice_fiscale = f.cf
LEFT JOIN geo cm ON lower(a.comune) = cm.comune_norm
ORDER BY cm.nome_provincia, a.comune, a.denominazione
