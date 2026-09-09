-- mart.sql — ETS + OpenCoesione: profilo coesione
-- Output: una riga per ETS con info coesione + temi per matching

SELECT
    codice_fiscale,
    denominazione,
    sezione,
    comune,
    provincia,
    ha_progetti_coesione,
    n_progetti_coesione,
    n_temi_coesione,
    max_progetto_coesione,
    temi_coesione,
    CASE
        WHEN n_progetti_coesione >= 10 THEN 'alto'
        WHEN n_progetti_coesione >= 3 THEN 'medio'
        WHEN n_progetti_coesione >= 1 THEN 'basso'
        ELSE 'nessuno'
    END as fascia_coesione
FROM clean_input
ORDER BY n_progetti_coesione DESC
