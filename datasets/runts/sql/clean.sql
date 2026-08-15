-- clean.sql — RUNTS (Registro Unico Nazionale del Terzo Settore)
-- Snapshot XLSX bilingue IT/DE dal Ministero del Lavoro.
-- Colonne raw rinominate in lettura via clean.read.columns (ordine XLSX).
-- Output: schema allineato a runts_iscritti.parquet (driver-first TSI).

SELECT
    normalize_string(codice_fiscale) AS codice_fiscale,
    TRY_CAST(normalize_string(repertorio) AS BIGINT) AS repertorio,
    normalize_string(denominazione) AS denominazione,
    normalize_string(sezione) AS sezione,
    normalize_string(rappresentante) AS rappresentante,
    normalize_string(rete) AS rete,
    normalize_string(comune) AS comune,
    normalize_string(provincia) AS provincia,
    normalize_string(flag_5x1000) AS flag_5x1000,
    TRY_STRPTIME(normalize_string(data_iscrizione), '%d/%m/%Y') AS data_iscrizione
FROM raw_input
WHERE codice_fiscale IS NOT NULL AND TRIM(codice_fiscale) != ''
