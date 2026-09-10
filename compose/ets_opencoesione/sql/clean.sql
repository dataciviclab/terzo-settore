-- clean.sql — Compose RUNTS + OpenCoesione
-- Quali ETS hanno partecipato a progetti di fondi coesione
-- Output: lungo formato (codice_fiscale, fonte, anno, importo) + dettagli coesione.
--
-- TODO: dopo PR merged in dataset-incubator, sostituire i path locali con GCS URL:
--   https://storage.googleapis.com/dataciviclab-clean/opencoesione_progetti/2026/...
--   https://storage.googleapis.com/dataciviclab-clean/opencoesione_soggetti/2026/...

WITH
anagrafe AS (
    SELECT codice_fiscale, denominazione, sezione, comune, provincia
    FROM raw_input
    WHERE codice_fiscale IS NOT NULL
      AND trim(codice_fiscale) != ''
),

fatti_coesione AS (
    SELECT
        s.OC_CODICE_FISCALE_SOGG as codice_fiscale,
        COUNT(DISTINCT p.COD_LOCALE_PROGETTO) as n_progetti,
        COUNT(DISTINCT p.OC_TEMA_SINTETICO) as n_temi,
        MAX(p.OC_FINANZ_TOT_PUB_NETTO) as max_finanziamento_progetto,
        GROUP_CONCAT(DISTINCT p.OC_TEMA_SINTETICO) as temi_coesione
    FROM read_parquet('{support.opencoesione_progetti.clean}') p
    JOIN read_parquet('{support.opencoesione_soggetti.clean}') s
        ON p.COD_LOCALE_PROGETTO = s.COD_LOCALE_PROGETTO
    WHERE s.SOGG_DESCR_RUOLO LIKE '%Beneficiario%'
      AND s.OC_CODICE_FISCALE_SOGG IS NOT NULL
      AND trim(s.OC_CODICE_FISCALE_SOGG) != ''
    GROUP BY s.OC_CODICE_FISCALE_SOGG
)

SELECT
    a.codice_fiscale,
    'coesione' as fonte,
    2026 as anno,
    0 as importo,
    a.denominazione,
    a.sezione,
    a.comune,
    a.provincia,
    CASE WHEN c.codice_fiscale IS NOT NULL THEN TRUE ELSE FALSE END as ha_progetti_coesione,
    COALESCE(c.n_progetti, 0) as n_progetti_coesione,
    COALESCE(c.n_temi, 0) as n_temi_coesione,
    COALESCE(c.max_finanziamento_progetto, 0) as max_progetto_coesione,
    COALESCE(c.temi_coesione, '') as temi_coesione
FROM anagrafe a
LEFT JOIN fatti_coesione c ON a.codice_fiscale = c.codice_fiscale
