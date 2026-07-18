"""Wrapper backward-compat: re-exporta da tsi.matching.engine.

Migrato. Il codice sorgente è ora in tsi/matching/engine.py.
Questo file garantisce che gli import esistenti continuino a funzionare.
"""

from tsi.matching.engine import *  # noqa: F401, F403
