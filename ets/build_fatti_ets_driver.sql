-- build_fatti_ets_driver.sql
-- Tabella long: una riga per (ETS, fonte, anno, importo)
-- ARCHITETTURA DRIVER-FIRST:
--   RUNTS (150k CF) è il driver → join filtrato con ogni fonte
--   Legge in-place dal layer clean del Lab (locale se c'è, GCS altrimenti)
--   Materializza SOLO le righe che matchano il RUNTS (non tutti i soggetti)
--
-- Source resolution:
--   locale:  ../dataset-incubator/out/data/clean/{slug}/{year}/{slug}_{year}_clean.parquet
--   remoto:  https://storage.googleapis.com/dataciviclab-clean/{slug}/{year}/{slug}_{year}_clean.parquet
-- La macro `p()` prova il path locale, fallback GCS.


COPY (
WITH runts_driver AS (
    SELECT DISTINCT TRIM(UPPER(codice_fiscale)) as cf
    FROM 'data/runts_iscritti.parquet'
),
cinque AS (
    SELECT TRIM(REPLACE(codice_fiscale, chr(39), '')) as cf, anno, importo_totale_erogabile as importo
    FROM read_parquet([
        {ade_cinque_per_mille_2023},
        {ade_cinque_per_mille_2024},
        {ade_cinque_per_mille_2025}
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
        {fts_eu_grants_2020},
        {fts_eu_grants_2021},
        {fts_eu_grants_2022},
        {fts_eu_grants_2023},
        {fts_eu_grants_2024}
    ], union_by_name=true)
    WHERE TRIM(beneficiario_partita_iva) != '-'
),
rna AS (
    SELECT TRIM(REPLACE(codice_fiscale_beneficiario, chr(39), '')) as cf, anno, importo_nominale as importo
    FROM read_parquet([
        {rna_aiuti_stato_2025},
        {rna_aiuti_stato_2026}
    ], union_by_name=true)
),
pnrr AS (
    SELECT TRIM(cf_soggetto_attuatore) as cf, 2026 as anno, fin_totale as importo
    FROM read_parquet({pnrr_progetti_2026}, union_by_name=true)
),
bandi_gara AS (
    SELECT * FROM read_parquet([
        {anac_bandi_gara_2023},
        {anac_bandi_gara_2024},
        {anac_bandi_gara_2025}
    ], union_by_name=true)
),
anac AS (
    WITH partecipanti_per_cig AS (
        SELECT cig, count(DISTINCT codice_fiscale) as n_part
        FROM read_parquet({anac_aggiudicatari_2026}, union_by_name=true)
        WHERE codice_fiscale IN (SELECT cf FROM runts_driver)
        GROUP BY cig
    ),
    per_cig AS (
        SELECT a.codice_fiscale as cf,
               a.cig,
               MAX(ag.importo_aggiudicazione) / GREATEST(MAX(COALESCE(p.n_part, 1)), 1) as importo,
               MAX(ag.data_aggiudicazione_definitiva) as data_max
        FROM read_parquet({anac_aggiudicatari_2026}, union_by_name=true) a
        JOIN read_parquet({anac_aggiudicazioni_2026}, union_by_name=true) ag
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
    SELECT TRIM(codice_fiscale) as cf,
           count(DISTINCT cig) as n_gare
    FROM read_parquet({anac_partecipanti_2026}, union_by_name=true)
    WHERE codice_fiscale IS NOT NULL AND codice_fiscale != ''
      AND codice_fiscale IN (SELECT cf FROM runts_driver)
    GROUP BY TRIM(codice_fiscale)
),
subappalti AS (
    SELECT cf_subappaltante as cf,
           EXTRACT(YEAR FROM data_autorizzazione) as anno,
           0 as importo
    FROM read_parquet({anac_subappalti_2026}, union_by_name=true)
    WHERE cf_subappaltante IS NOT NULL AND cf_subappaltante != ''
      AND cf_subappaltante IN (SELECT cf FROM runts_driver)
      AND EXTRACT(YEAR FROM data_autorizzazione) BETWEEN 2000 AND 2026
),
patrimonio AS (
    SELECT REPLACE(REPLACE(soggetto_ricevente_cf, '[', ''), ']', '') as cf,
           anno,
           COALESCE(canone_annuale, 0) as importo
    FROM read_parquet({mef_patrimonio_detenzioni_2023}, union_by_name=true)
    WHERE soggetto_ricevente_cf IS NOT NULL AND soggetto_ricevente_cf != ''
      AND anno BETWEEN 2000 AND 2026
)
SELECT '5x1000' as fonte, cf, anno, importo, NULL as oggetto_gara, NULL as stazione_appaltante, NULL as appalto_riservato, NULL as flag_pnrr FROM cinque WHERE cf IN (SELECT cf FROM runts_driver)
UNION ALL
SELECT 'partecipazione', cf, 2026 as anno, n_gare as importo, NULL, NULL, NULL, NULL FROM partecipanti WHERE cf IN (SELECT cf FROM runts_driver)
UNION ALL
SELECT 'grant_ue', cf, anno, importo, NULL, NULL, NULL, NULL FROM fts WHERE cf IN (SELECT cf FROM runts_driver)
UNION ALL
SELECT 'aiuto_stato', cf, anno, importo, NULL, NULL, NULL, NULL FROM rna WHERE cf IN (SELECT cf FROM runts_driver)
UNION ALL
SELECT 'pnrr', cf, anno, importo, NULL, NULL, NULL, NULL FROM pnrr WHERE cf IN (SELECT cf FROM runts_driver)
UNION ALL
SELECT 'anac', cf, anno, importo, oggetto_gara, stazione_appaltante, appalto_riservato, flag_pnrr FROM anac WHERE cf IN (SELECT cf FROM runts_driver)
UNION ALL
SELECT 'subappalto', cf, anno, importo, NULL, NULL, NULL, NULL FROM subappalti WHERE cf IN (SELECT cf FROM runts_driver)
UNION ALL
SELECT 'patrimonio', cf, anno, importo, NULL, NULL, NULL, NULL FROM patrimonio WHERE cf IN (SELECT cf FROM runts_driver)
)
TO 'data/fatti_ets.parquet' (FORMAT PARQUET);
