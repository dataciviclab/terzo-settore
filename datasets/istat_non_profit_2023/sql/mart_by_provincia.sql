-- mart_by_provincia.sql — Istituzioni/dipendenti per provincia

SELECT
    codice_provincia,
    regione as provincia,
    istituzioni,
    dipendenti,
    ROUND(dipendenti::DOUBLE / NULLIF(istituzioni, 0), 1) as media_dipendenti_per_istituzione
FROM clean_input
WHERE livello = 'provincia'
ORDER BY istituzioni DESC
