-- mart_by_regione.sql — Totale istituzioni/dipendenti per regione (escluso ITALIA)

SELECT
    regione,
    SUM(CASE WHEN categoria_tipo = 'forma_giuridica' AND categoria = 'Associazione' THEN istituzioni END) as associazioni,
    SUM(CASE WHEN categoria_tipo = 'forma_giuridica' AND categoria = 'Cooperativa sociale' THEN istituzioni END) as cooperative,
    SUM(CASE WHEN categoria_tipo = 'forma_giuridica' AND categoria = 'Fondazione' THEN istituzioni END) as fondazioni,
    SUM(CASE WHEN categoria_tipo = 'forma_giuridica' AND categoria = 'Altra forma giuridica' THEN istituzioni END) as altra_forma,
    SUM(CASE WHEN categoria_tipo = 'forma_giuridica' THEN istituzioni END) as istituzioni_totali,
    SUM(CASE WHEN categoria_tipo = 'forma_giuridica' THEN dipendenti END) as dipendenti_totali,
    ROUND(SUM(CASE WHEN categoria_tipo = 'forma_giuridica' THEN dipendenti END)::DOUBLE /
          NULLIF(SUM(CASE WHEN categoria_tipo = 'forma_giuridica' THEN istituzioni END), 0), 1) as media_dipendenti_per_istituzione
FROM clean_input
WHERE livello = 'regione'
  AND regione != 'ITALIA'
GROUP BY regione
ORDER BY istituzioni_totali DESC
