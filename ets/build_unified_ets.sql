-- build_unified_ets.sql
-- Hub ETS: RUNTS (anagrafe) + PIVOT da fatti_ets + geografia + temi ANAC
-- fatti_ets.parquet deve essere stato generato dal driver-first (resolve_sources.py)
-- Output: una riga per ETS con tutti gli indicatori di capacità

COPY (
WITH anagrafe AS (
    SELECT
        codice_fiscale,
        denominazione,
        sezione,
        comune,
        provincia,
        data_iscrizione
    FROM read_parquet('data/runts_iscritti.parquet', union_by_name=true)
),

fatti_pivot AS (
    SELECT cf,
        -- 5x1000
        COUNT(CASE WHEN fonte = '5x1000' THEN 1 END) as anni_5x1000,
        SUM(CASE WHEN fonte = '5x1000' THEN importo END) as importo_5x1000_totale,
        MAX(CASE WHEN fonte = '5x1000' AND anno = 2025 THEN importo END) as importo_5x1000_2025,

        -- Grant UE
        COUNT(CASE WHEN fonte = 'grant_ue' THEN 1 END) as progetti_ue,
        SUM(CASE WHEN fonte = 'grant_ue' THEN importo END) as importo_ue,

        -- Aiuti di Stato
        COUNT(CASE WHEN fonte = 'aiuto_stato' THEN 1 END) as progetti_aiuti_stato,
        SUM(CASE WHEN fonte = 'aiuto_stato' THEN importo END) as importo_aiuti_stato,

        -- PNRR
        COUNT(CASE WHEN fonte = 'pnrr' THEN 1 END) as progetti_pnrr,
        SUM(CASE WHEN fonte = 'pnrr' THEN importo END) as importo_pnrr,

        -- Appalti pubblici ANAC
        COUNT(CASE WHEN fonte = 'anac' THEN 1 END) as numero_appalti,
        SUM(CASE WHEN fonte = 'anac' THEN importo END) as importo_appalti,
        COUNT(CASE WHEN fonte = 'anac' AND appalto_riservato IS NOT NULL AND appalto_riservato != ''
                    AND appalto_riservato != 'LA PARTECIPAZIONE NON È RISERVATA.' THEN 1 END) as appalti_riservati,
        COUNT(CASE WHEN fonte = 'anac' AND flag_pnrr = true THEN 1 END) as appalti_pnrr,

        -- Subappalti
        COUNT(CASE WHEN fonte = 'subappalto' THEN 1 END) as subappalti,

        -- Patrimonio immobiliare pubblico
        COUNT(CASE WHEN fonte = 'patrimonio' THEN 1 END) as patrimonio_immobili,
        SUM(CASE WHEN fonte = 'patrimonio' THEN importo END) as canone_totale

    FROM read_parquet('data/fatti_ets.parquet')
    GROUP BY cf
),

geo AS (
    SELECT lower(denominazione) as comune_norm, codice_istat, sigla_provincia, provincia as nome_provincia, regione
    FROM read_parquet('../dataset-incubator/out/data/clean/comuni_master/2026/comuni_master_2026_clean.parquet', union_by_name=true)
)

SELECT
    a.codice_fiscale,
    a.denominazione,
    a.sezione,
    a.comune,
    cm.codice_istat,
    COALESCE(cm.sigla_provincia, a.provincia) as provincia,
    cm.regione,
    a.data_iscrizione,

    -- 5x1000
    CASE WHEN COALESCE(importo_5x1000_2025, 0) > 0 THEN TRUE ELSE FALSE END as ha_5x1000,
    importo_5x1000_2025,
    COALESCE(importo_5x1000_totale, 0) as importo_5x1000_totale,
    COALESCE(anni_5x1000, 0) as anni_5x1000,
    regexp_matches(lower(a.denominazione), '(asd|associazione sportiva|società sportiva|sportiva dilettantistica|polisportiva)') as ha_sport_in_denominazione,

    -- Grant UE
    CASE WHEN COALESCE(importo_ue, 0) > 0 THEN TRUE ELSE FALSE END as ha_finanziamenti_ue,
    COALESCE(progetti_ue, 0) as progetti_ue,
    COALESCE(importo_ue, 0) as importo_ue,

    -- Aiuti di Stato
    CASE WHEN COALESCE(importo_aiuti_stato, 0) > 0 THEN TRUE ELSE FALSE END as ha_aiuti_stato,
    COALESCE(progetti_aiuti_stato, 0) as progetti_aiuti_stato,
    COALESCE(importo_aiuti_stato, 0) as importo_aiuti_stato,

    -- PNRR
    CASE WHEN COALESCE(importo_pnrr, 0) > 0 THEN TRUE ELSE FALSE END as ha_progetti_pnrr,
    COALESCE(progetti_pnrr, 0) as progetti_pnrr,
    COALESCE(importo_pnrr, 0) as importo_pnrr,

    -- Appalti pubblici ANAC
    CASE WHEN COALESCE(importo_appalti, 0) > 0 THEN TRUE ELSE FALSE END as ha_appalti_pubblici,
    COALESCE(numero_appalti, 0) as numero_appalti,
    COALESCE(importo_appalti, 0) as importo_appalti,
    COALESCE(appalti_riservati, 0) as appalti_riservati,
    COALESCE(appalti_pnrr, 0) as appalti_pnrr,
    COALESCE(subappalti, 0) as subappalti,
    COALESCE(patrimonio_immobili, 0) as patrimonio_immobili,
    COALESCE(canone_totale, 0) as canone_totale,

    -- Temi ANAC
    COALESCE(ta.temi_anac, '') as temi_anac,

    -- Indicatore composito di capacità
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
LEFT JOIN read_parquet('data/temi_anac.parquet', union_by_name=true) ta ON a.codice_fiscale = ta.codice_fiscale
ORDER BY cm.nome_provincia, a.comune, a.denominazione
)
TO 'data/unified_ets.parquet' (FORMAT PARQUET);
