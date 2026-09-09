-- mart_by_settore.sql — Istituzioni per settore e regione

SELECT
    regione,
    categoria as settore,
    istituzioni,
    dipendenti
FROM clean_input
WHERE livello = 'regione'
  AND categoria_tipo = 'settore'
  AND regione != 'ITALIA'
ORDER BY istituzioni DESC
