-- mart_comuni.sql — Aggregato ETS per comune
-- Consuma clean_input (unified_ets) e produce metriche per comune.

SELECT
    comune,
    provincia,
    codice_istat,
    count(*) as ets_tot,
    count(*) FILTER (WHERE capacita_progettuale IN ('alta', 'medio-alta', 'media')) as ets_matchabili,
    count(*) FILTER (WHERE capacita_progettuale = 'alta') as capacita_alta,
    count(*) FILTER (WHERE sezione = 'ORGANIZZAZIONI DI VOLONTARIATO') as odv,
    count(*) FILTER (WHERE sezione = 'ASSOCIAZIONI DI PROMOZIONE SOCIALE') as aps,
    count(*) FILTER (WHERE sezione = 'IMPRESE SOCIALI') as imprese_sociali,
    count(*) FILTER (WHERE ha_finanziamenti_ue) as con_grant_ue,
    count(*) FILTER (WHERE ha_progetti_pnrr) as con_pnrr,
    count(*) FILTER (WHERE ha_sport_in_denominazione) as sport,
    count(*) FILTER (WHERE ha_appalti_pubblici) as con_appalti,
    sum(CASE WHEN ha_appalti_pubblici THEN importo_appalti ELSE 0 END) as importo_appalti_totale,
    count(*) FILTER (WHERE capacita_progettuale = 'sconosciuta') as ets_sconosciuti
FROM clean_input
GROUP BY comune, provincia, codice_istat
HAVING ets_tot > 0
ORDER BY ets_tot DESC
