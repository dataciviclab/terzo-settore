-- mart_runts_sezione.sql — conteggi RUNTS per sezione
-- Aggregato di verifica per un dataset anagrafico snapshot.

SELECT
    sezione,
    count(*) AS enti,
    count(DISTINCT provincia) AS province,
    min(data_iscrizione) AS prima_iscrizione,
    max(data_iscrizione) AS ultima_iscrizione
FROM clean_input
GROUP BY sezione
ORDER BY enti DESC
