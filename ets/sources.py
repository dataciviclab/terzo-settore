# ets/sources.py — Fonte di verità delle dipendenze dati del TSI.
# (slug, year, filename) — stessa struttura della vecchia lista di _scripts/gcs_cache.py
# Legge dal layer clean del Lab (locale) o da GCS (remoto), vedi resolve_sources.py.

SOURCES = [
    ("anac_aggiudicatari", 2026, "anac_aggiudicatari_2026_clean.parquet"),
    ("anac_aggiudicazioni", 2026, "anac_aggiudicazioni_2026_clean.parquet"),
    ("anac_partecipanti", 2026, "anac_partecipanti_2026_clean.parquet"),
    ("anac_bandi_gara", 2023, "anac_bandi_gara_2023_clean.parquet"),
    ("anac_bandi_gara", 2024, "anac_bandi_gara_2024_clean.parquet"),
    ("anac_bandi_gara", 2025, "anac_bandi_gara_2025_clean.parquet"),
    ("anac_subappalti", 2026, "anac_subappalti_2026_clean.parquet"),
    ("mef_patrimonio_detenzioni", 2023, "mef_patrimonio_detenzioni_2023_clean.parquet"),
    ("ade_cinque_per_mille", 2023, "ade_cinque_per_mille_2023_clean.parquet"),
    ("ade_cinque_per_mille", 2024, "ade_cinque_per_mille_2024_clean.parquet"),
    ("ade_cinque_per_mille", 2025, "ade_cinque_per_mille_2025_clean.parquet"),
    ("fts_eu_grants", 2020, "fts_eu_grants_2020_clean.parquet"),
    ("fts_eu_grants", 2021, "fts_eu_grants_2021_clean.parquet"),
    ("fts_eu_grants", 2022, "fts_eu_grants_2022_clean.parquet"),
    ("fts_eu_grants", 2023, "fts_eu_grants_2023_clean.parquet"),
    ("fts_eu_grants", 2024, "fts_eu_grants_2024_clean.parquet"),
    ("rna_aiuti_stato", 2025, "rna_aiuti_stato_2025_clean.parquet"),
    ("rna_aiuti_stato", 2026, "rna_aiuti_stato_2026_clean.parquet"),
    ("pnrr_progetti", 2026, "pnrr_progetti_2026_clean.parquet"),
    ("comuni_master", 2026, "comuni_master_2026_clean.parquet"),
]
