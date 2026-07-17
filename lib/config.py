"""Paths, thresholds e costanti del sistema."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Dataset
ETS_FILE = ROOT / "data/unified_ets.parquet"
RUNTS_FILE = ROOT / "data/runts_iscritti.parquet"
OC_PARQUET = ROOT / "data/oc_organizzazioni.parquet"

# Bandi
BANDI_FILES = [
    ROOT / "data/bandi/infobandi_bandi.json",
    ROOT / "data/bandi/info_cooperazione_bandi.json",
]

# Output
RADAR_REPORT = ROOT / "cruscotto/radar-completo.md"
SEGNALE_DIR = ROOT / "cruscotto"

# Soglie capacità
CAP_GRANT_UE = 0          # >0 → alta
CAP_AIUTI_STATO = 0       # >0 → medio-alta
CAP_PNRR = 0              # >0 → medio-alta
CAP_CINQUE_SINGOLO = 10000  # > soglia → media
CAP_CINQUE_ANNI = 3         # >= → media
CAP_OC_BILANCIO = 100000   # > soglia → media
CAP_OC_PROGETTI = 3         # >= → media
CAP_OC_DIPENDENTI = 3       # >= → media

# Enrichment
PLACES_SEARCH_RADIUS = 500  # metri
PLACES_CACHE_DIR = ROOT / "data/enrich"
