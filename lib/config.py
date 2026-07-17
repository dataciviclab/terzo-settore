"""Paths, thresholds e costanti del sistema."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Dataset
ETS_FILE = ROOT / "data/unified_ets.parquet"

# Bandi
BANDI_FILES = [
    ROOT / "data/bandi/infobandi_bandi.json",
    ROOT / "data/bandi/info_cooperazione_bandi.json",
]

# Output
RADAR_REPORT = ROOT / "cruscotto/radar-completo.md"

# Soglie capacità (usate in build_unified_ets.sql)
CAP_GRANT_UE = 0
CAP_AIUTI_STATO = 0
CAP_PNRR = 0
CAP_CINQUE_SINGOLO = 10000
CAP_CINQUE_ANNI = 3
CAP_OC_BILANCIO = 100000
CAP_OC_PROGETTI = 3
CAP_OC_DIPENDENTI = 3
