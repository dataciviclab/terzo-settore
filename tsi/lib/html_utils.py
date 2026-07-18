"""HTML fallback: estrae dati da pagine bando — re-export da lib/html_utils.py."""

import sys
from pathlib import Path

# Aggiunge lib/ al path per import
_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root / "lib"))

from html_utils import arricchisci  # noqa: E402, F401
