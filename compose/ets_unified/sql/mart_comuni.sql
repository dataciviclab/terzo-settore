-- mart_comuni.sql — Aggregato ETS per comune
-- Consuma clean_input (fatti_ets long: cf, fonte, anno, importo) e produce metriche per comune.
-- Legge anche RUNTS per anagrafe comune e sezione.

WITH
anagrafe AS (
    SELECT codice_fiscale, comune, provincia, sezione
    FROM '{support.runts.clean}'
),

fatti_pivot AS (
    SELECT cf,
        COUNT(CASE WHEN fonte = 'anac_aggiudicazione' THEN 1 END) as numero_appalti,
        SUM(CASE WHEN fonte = 'anac_aggiudicazione' THEN importo END) as importo_appalti,
        CASE WHEN SUM(CASE WHEN fonte = 'grant_ue' THEN importo END) > 0 THEN TRUE ELSE FALSE END as ha_finanziamenti_ue,
        CASE WHEN SUM(CASE WHEN fonte = 'pnrr' THEN importo END) > 0 THEN TRUE ELSE FALSE END as ha_progetti_pnrr,
        CASE WHEN MAX(CASE WHEN fonte = '5x1000' AND anno = 2025 THEN importo END) > 0 THEN TRUE ELSE FALSE END as ha_5x1000
    FROM clean_input
    GROUP BY cf
),

unificato AS (
    SELECT
        a.codice_fiscale,
        a.comune,
        a.provincia,
        a.sezione,
        COALESCE(f.numero_appalti, 0) as numero_appalti,
        COALESCE(f.importo_appalti, 0) as importo_appalti,
        COALESCE(f.ha_finanziamenti_ue, FALSE) as ha_finanziamenti_ue,
        COALESCE(f.ha_progetti_pnrr, FALSE) as ha_progetti_pnrr,
        COALESCE(f.ha_5x1000, FALSE) as ha_5x1000,
        CASE
            WHEN COALESCE(f.ha_finanziamenti_ue, FALSE) THEN 'alta'
            WHEN COALESCE(f.numero_appalti, 0) >= 10 THEN 'alta'
            WHEN COALESCE(f.numero_appalti, 0) >= 3 THEN 'medio-alta'
            WHEN COALESCE(f.numero_appalti, 0) >= 1 THEN 'media'
            WHEN COALESCE(f.ha_5x1000, FALSE) THEN 'base'
            WHEN a.sezione = 'IMPRESE SOCIALI' THEN 'base'
            ELSE 'sconosciuta'
        END as capacita_progettuale
    FROM anagrafe a
    LEFT JOIN fatti_pivot f ON a.codice_fiscale = f.cf
)

SELECT
    comune,
    provincia,
    count(*) as ets_tot,
    count(*) FILTER (WHERE capacita_progettuale IN ('alta', 'medio-alta', 'media')) as ets_matchabili,
    count(*) FILTER (WHERE capacita_progettuale = 'alta') as capacita_alta,
    count(*) FILTER (WHERE sezione = 'ORGANIZZAZIONI DI VOLONTARIATO') as odv,
    count(*) FILTER (WHERE sezione = 'ASSOCIAZIONI DI PROMOZIONE SOCIALE') as aps,
    count(*) FILTER (WHERE sezione = 'IMPRESE SOCIALI') as imprese_sociali,
    count(*) FILTER (WHERE ha_finanziamenti_ue) as con_grant_ue,
    count(*) FILTER (WHERE ha_progetti_pnrr) as con_pnrr,
    count(*) FILTER (WHERE numero_appalti > 0) as con_appalti,
    sum(CASE WHEN numero_appalti > 0 THEN importo_appalti ELSE 0 END) as importo_appalti_totale,
    count(*) FILTER (WHERE capacita_progettuale = 'sconosciuta') as ets_sconosciuti
FROM unificato
GROUP BY comune, provincia
HAVING ets_tot > 0
ORDER BY ets_tot DESC
