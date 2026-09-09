-- clean.sql — ISTAT Non Profit 2023: Excel parse
-- Input: raw_input (long format: anno, regione, livello, categoria_tipo, categoria, istituzioni, dipendenti)
-- Output: clean con totale per regione

SELECT
    anno,
    regione,
    livello,
    categoria_tipo,
    categoria,
    istituzioni,
    dipendenti,
    codice_provincia
FROM raw_input
WHERE istituzioni > 0
