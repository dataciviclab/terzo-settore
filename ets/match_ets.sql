SELECT codice_fiscale, denominazione, comune, provincia, capacita_progettuale,
       importo_5x1000_2025, ha_sport_in_denominazione, sezione,
       ha_finanziamenti_ue, ha_progetti_pnrr, ha_appalti_pubblici, numero_appalti, importo_appalti,
       COALESCE(temi_anac, '') as temi_anac,
       CASE
         WHEN {match_tema} AND ha_sport_in_denominazione AND {sez_match_bool} THEN 'tema+sport+sezione'
         WHEN {match_tema} AND ha_sport_in_denominazione THEN 'tema+sport'
         WHEN {match_tema} AND {sez_match_bool} THEN 'tema+sezione'
         WHEN {match_tema} THEN 'tema'
         WHEN ha_sport_in_denominazione THEN 'sport'
         WHEN {sez_match_bool} THEN 'sezione'
         ELSE 'match'
       END AS motivo_match,
       (
         CASE WHEN {match_tema} THEN 10 ELSE 0 END
         + CASE WHEN {sez_match_bool} THEN 25 ELSE 0 END
         + CASE WHEN ha_sport_in_denominazione AND {sport_bonus} THEN 15 ELSE 0 END
         {section_bonus}
         + CASE capacita_progettuale
             WHEN 'alta' THEN 25 WHEN 'medio-alta' THEN 20 WHEN 'media' THEN 10 ELSE 0 END
         + CASE WHEN importo_5x1000_2025 >= 100000 THEN 15
                WHEN importo_5x1000_2025 >= 10000 THEN 10
                WHEN importo_5x1000_2025 > 0 THEN 5 ELSE 0 END
         + CASE WHEN ha_finanziamenti_ue THEN 8 ELSE 0 END
         + CASE WHEN ha_progetti_pnrr THEN 5 ELSE 0 END
         + CASE WHEN numero_appalti >= 50 THEN 15
                WHEN numero_appalti >= 20 THEN 12
                WHEN numero_appalti >= 10 THEN 10
                WHEN numero_appalti >= 5 THEN 7
                WHEN numero_appalti >= 1 THEN 5 ELSE 0 END
         + CASE WHEN sezione = 'IMPRESI SOCIALI' THEN 5 ELSE 0 END
       ) AS score
FROM '{ets_file}'
WHERE {match_condition}
  AND (capacita_progettuale IN ('media', 'medio-alta', 'alta')
       OR ha_appalti_pubblici = true
       OR ha_5x1000 = true
       OR ha_finanziamenti_ue = true
       OR ha_progetti_pnrr = true)
  {province_filter}
ORDER BY score DESC, importo_5x1000_2025 DESC NULLS LAST
LIMIT {limit}
