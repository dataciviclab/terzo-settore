-- clean.sql — RUNTS (Registro Unico Nazionale del Terzo Settore)
-- Snapshot XLSX bilingue IT/DE dal Ministero del Lavoro.
-- Colonne raw rinominate in lettura via clean.read.columns (ordine XLSX).
-- Output: schema allineato a runts_iscritti.parquet (driver-first TSI).
--
-- Fix noti:
--   - Provincia NULL: comuni della citta metropolitana di Napoli senza mappatura nel XLSX
--   - Sezione "-": reti associative senza sezione standard → trasformata in NULL
--   - Denominazione: strip apici singoli/doppii allinizio/fine, normalizza tipografici

WITH raw AS (
    SELECT
        normalize_string(codice_fiscale) AS codice_fiscale,
        cast_bigint(normalize_string(repertorio)) AS repertorio,
        normalize_string(sezione) AS sezione,
        normalize_string(rappresentante) AS rappresentante,
        normalize_string(rete) AS rete,
        normalize_string(comune) AS comune,
        normalize_string(provincia) AS provincia,
        normalize_string(flag_5x1000) AS flag_5x1000,
        TRY_STRPTIME(normalize_string(data_iscrizione), '%d/%m/%Y') AS data_iscrizione,
        REPLACE(REPLACE(denominazione, chr(8216), chr(39)), chr(8217), chr(39)) AS _denom_raw
    FROM raw_input
    WHERE codice_fiscale IS NOT NULL AND TRIM(codice_fiscale) != ''
)
SELECT
    codice_fiscale,
    repertorio,
    TRIM(BOTH '"' FROM TRIM(BOTH chr(39) FROM _denom_raw)) AS denominazione,
    CASE WHEN sezione = '-' THEN NULL ELSE sezione END AS sezione,
    rappresentante,
    rete,
    comune,
    CASE
        WHEN provincia IS NOT NULL THEN provincia
        WHEN comune IN (
            'NAPOLI','GIUGLIANO IN CAMPANIA','TORRE DEL GRECO','NOLA','ACERRA',
            'POZZUOLI','PORTICI','CASTELLAMMARE DI STABIA','CASORIA',
            'SAN GIORGIO A CREMANO','AFRAGOLA','POMIGLIANO D''ARCO',
            'CASALNUOVO DI NAPOLI','TORRE ANNUNZIATA','SOMMA VESUVIANA',
            'CRISPANO','BACOLI','SAN VITALIANO','CIMITILE','SAN GENNARO VESUVIANO',
            'MARCIANISE','GRAGNANO','SANT''ANTONIO ABATE','VOLLA',
            'MONTE DI PROCIDA','LACCO AMENO','FORIO','SERRARA FONTANA',
            'CASAMICCIOLA TERME','BARANO D''ISCHIA','MARANO DI NAPOLI',
            'QUARTO','CALVIZZANO','VILLARICCA','CHIAIANO',
            'FRATTAMAGGIORE','FRATTAMINORE','GRUMO NEVANO','SANT''ARPINO',
            'SANT''ANTIMO','CASAVATORE','MELITO DI NAPOLI',
            'ERCOLANO','VICO EQUENSE','MARIGLIANO','ISCHIA','POMPEI',
            'MUGNANO DI NAPOLI','SORRENTO','POGGIOMARINO','CERCOLA',
            'SAN GIUSEPPE VESUVIANO','CARDITO','CICCIANO','BOSCOREALE',
            'CAIVANO','PALMA CAMPANIA','OTTAVIANO','ARZANO','SAVIANO',
            'POLLENA TROCCHIA','SANT''ANASTASIA','BRUSCIANO','TERZIGNO',
            'MASSA DI SOMMA','SIANO'
        ) THEN 'NA'
        ELSE provincia
    END AS provincia,
    flag_5x1000,
    data_iscrizione
FROM raw
