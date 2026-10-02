-- clean.sql — Compose RUNTS + ANAC (3 pezzi)
-- 1. Aggiudicazioni: CF + importo + oggetto + stazione
-- 2. Partecipazioni: CF + conteggio gare
-- 3. Subappalti: CF + boolean

WITH
anagrafe AS (
    SELECT codice_fiscale
    FROM raw_input
    WHERE codice_fiscale IS NOT NULL
      AND trim(codice_fiscale) != ''
),

-- ── 1. Aggiudicazioni (CF + importo + dettagli) ─────────────────────
bandi_gara AS (
    SELECT cig, oggetto_lotto, oggetto_gara,
           denominazione_amministrazione_appaltante,
           TIPO_APPALTO_RISERVATO, flag_pnrr,
           descrizione_cpv, settore
    FROM read_parquet({support.anac_bandi_gara.clean}, union_by_name=true)
),

-- Conteggio partecipanti per CIG — solo i CIG con aggiudicatari ETS
tutti_partecipanti AS (
    SELECT cig, count(DISTINCT codice_fiscale) as n_part
    FROM '{support.anac_aggiudicatari.path}'
    WHERE codice_fiscale IS NOT NULL AND codice_fiscale != ''
      AND codice_fiscale IN (SELECT codice_fiscale FROM anagrafe)
    GROUP BY cig
),

aggiudicazioni AS (
    WITH per_cig AS (
        SELECT a.codice_fiscale, a.cig,
               MAX(ag.importo_aggiudicazione) / GREATEST(MAX(COALESCE(tp.n_part, 1)), 1) as importo,
               MAX(ag.data_aggiudicazione_definitiva) as data_max
        FROM '{support.anac_aggiudicatari.path}' a
        JOIN '{support.anac_aggiudicazioni.path}' ag
          ON a.id_aggiudicazione = ag.id_aggiudicazione
        LEFT JOIN tutti_partecipanti tp ON a.cig = tp.cig
        WHERE a.codice_fiscale IS NOT NULL AND a.codice_fiscale != ''
          AND a.codice_fiscale IN (SELECT codice_fiscale FROM anagrafe)
          AND ag.importo_aggiudicazione > 0
          AND ag.importo_aggiudicazione < 100000000000
          AND EXTRACT(YEAR FROM ag.data_aggiudicazione_definitiva) BETWEEN 2000 AND 2026
        GROUP BY a.codice_fiscale, a.cig
    )
    SELECT p.codice_fiscale,
           EXTRACT(YEAR FROM p.data_max) as anno,
           p.importo,
           COALESCE(bg.oggetto_lotto, bg.oggetto_gara) as oggetto_gara,
           bg.denominazione_amministrazione_appaltante as stazione_appaltante,
           bg.TIPO_APPALTO_RISERVATO as appalto_riservato,
           bg.flag_pnrr,
           bg.descrizione_cpv,
           bg.settore,
           COALESCE(tp.n_part, 1) as n_part,
           CASE WHEN COALESCE(tp.n_part, 1) > 1 THEN TRUE ELSE FALSE END as appalto_multiplo
    FROM per_cig p
    LEFT JOIN bandi_gara bg ON p.cig = bg.cig
    LEFT JOIN tutti_partecipanti tp ON p.cig = tp.cig
),

-- ── 2. Partecipazioni (CF + conteggio gare) ────────────────────────
partecipazioni AS (
    SELECT TRIM(codice_fiscale) as codice_fiscale, count(DISTINCT cig) as n_gare
    FROM '{support.anac_partecipanti.path}'
    WHERE codice_fiscale IS NOT NULL AND codice_fiscale != ''
      AND codice_fiscale IN (SELECT codice_fiscale FROM anagrafe)
      AND tipo_soggetto NOT ILIKE '%STAZIONE APPALTANTE%'
    GROUP BY TRIM(codice_fiscale)
),

-- ── 3. Subappalti (CF + boolean) ───────────────────────────────────
subappalti AS (
    SELECT cf_subappaltante as codice_fiscale,
           EXTRACT(YEAR FROM data_autorizzazione) as anno,
           0 as importo
    FROM '{support.anac_subappalti.path}'
    WHERE cf_subappaltante IS NOT NULL AND cf_subappaltante != ''
      AND cf_subappaltante IN (SELECT codice_fiscale FROM anagrafe)
      AND EXTRACT(YEAR FROM data_autorizzazione) BETWEEN 2000 AND 2026
)

-- Output: long format con fonte per distinguere i 3 pezzi
SELECT 'anac_aggiudicazione' as fonte, codice_fiscale, anno, importo, oggetto_gara, stazione_appaltante, appalto_riservato, flag_pnrr, NULL as n_gare, descrizione_cpv, settore, n_part, appalto_multiplo FROM aggiudicazioni
UNION ALL SELECT 'anac_partecipazione', codice_fiscale, 2026, NULL, NULL, NULL, NULL, NULL, n_gare, NULL, NULL, NULL, FALSE FROM partecipazioni
UNION ALL SELECT 'anac_subappalto', codice_fiscale, anno, importo, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, FALSE FROM subappalti
