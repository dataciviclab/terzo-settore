"""Funnel di matching a 3 stadi: idoneità → pertinenza → ranking.

Rispetto al matching additivo originale (tema OR + capacità somma), il funnel:

  STAGE 1 · IDONEITÀ — esclusione HARD (sezione RUNTS + territorio)
  STAGE 2 · PERTINENZA — match sul tema PRINCIPALE del bando (stretto)
                        + match debole su tag secondari
  STAGE 3 · RANKING — pertinenza × capacità (non somma)

Design:
- Il tema principale è un FILTRO (chi non lo matcha non passa, o passa
  solo come "secondario" con score ridotto)
- La capacità finanziaria è un MOLTIPLICATORE della pertinenza, non un
  sostituto — così i "grandi ricchi non pertinenti" non dominano più
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from config import ETS_FILE, get_province_filter
from temi import TEMA_PATTERN, estrai_temi, normalizza_tags, sezioni_per_tag, tema_principale


# ── Stage 1: idoneità ──────────────────────────────────────────────

def gate_sezione(tags, testo=None) -> str:
    """Sezioni RUNTS ammesse per il TEMA PRINCIPALE del bando. '' = nessun gate.

    Usa solo il tema principale (non l'unione di tutti i tag): un bando di
    sport per disabili è comunque APS (sport), non imprese sociali (disabilità).
    """
    tema = tema_principale(tags, testo)
    if not tema:
        return ""
    sezioni = sezioni_per_tag([tema])
    if not sezioni:
        return ""
    quote = ", ".join(f"'{s}'" for s in sezioni)
    return f"AND sezione IN ({quote})"


def gate_territorio(territorio) -> str:
    """Filtro provincia/regione se il bando è locale. '' = nessun gate."""
    if not territorio:
        return ""
    province = get_province_filter(territorio)
    if not province:
        return ""
    quote = ", ".join(f"'{p}'" for p in province)
    return f"AND provincia IN ({quote})"


# ── Stage 2: pertinenza ────────────────────────────────────────────

def _cond(p):
    return f"(regexp_matches(lower(denominazione), '{p}'))"


def _cond_temi(p):
    return f"(regexp_matches(temi_anac, '{p}'))"


def match_tema_sql(tags, testo=None):
    """Costruisce la condizione SQL di pertinenza.

    Ritorna (condizione, motivo_col):
      - match PRINCIPALE: denominazione matcha il tema dominante (FORTE)
      - match SECONDARIO: denominazione matcha altri tag (DEBOLE)
      - temi_anac matcha: boost debole (ha mai operato nel tema), mai
        come match principale — evita che i grandi enti "tuttofare"
        (temi_anac pieni) dominino il ranking
    """
    tema_prim = tema_principale(tags, testo)
    pattern_prim = TEMA_PATTERN.get(tema_prim) if tema_prim else None

    normalizzati = normalizza_tags(tags)
    if not normalizzati and testo:
        normalizzati = estrai_temi(testo)

    pattern_sec_parts = []
    for t in normalizzati:
        if t == tema_prim:
            continue
        p = TEMA_PATTERN.get(t)
        if p:
            pattern_sec_parts.append(p)
    pattern_sec = "|".join(pattern_sec_parts) if pattern_sec_parts else None

    prim_denom = _cond(pattern_prim) if pattern_prim else None
    sec_denom = _cond(pattern_sec) if pattern_sec else None
    prim_temi = _cond_temi(pattern_prim) if pattern_prim else None

    if prim_denom:
        # principale: denominazione matcha il tema dominante
        # secondario: denominazione matcha un altro tag, OPPURE temi_anac
        #             matcha il tema principale (boost debole)
        if sec_denom:
            cond = f"({prim_denom} OR {sec_denom} OR {prim_temi})"
            motivo = (
                f"CASE WHEN {prim_denom} THEN 'tema_principale' "
                f"WHEN {sec_denom} THEN 'tema_secondario' "
                f"WHEN {prim_temi} THEN 'tema_temi_anac' ELSE NULL END"
            )
        else:
            cond = f"({prim_denom} OR {prim_temi})"
            motivo = (
                f"CASE WHEN {prim_denom} THEN 'tema_principale' "
                f"WHEN {prim_temi} THEN 'tema_temi_anac' ELSE NULL END"
            )
        return cond, motivo
    if sec_denom:
        return sec_denom, f"CASE WHEN {sec_denom} THEN 'tema_secondario' ELSE NULL END"
    return "1=0", "NULL"


# ── Stage 3: ranking (pertinenza × capacità) ───────────────────────

SCORE_SQL = """
    (CASE
        WHEN motivo_match = 'tema_principale' THEN 100
        WHEN motivo_match = 'tema_secondario' THEN 60
        WHEN motivo_match = 'tema_temi_anac' THEN 30
        ELSE 10
    END)
    + (CASE capacita_progettuale
        WHEN 'alta' THEN 25 WHEN 'medio-alta' THEN 18
        WHEN 'media' THEN 12 WHEN 'base' THEN 6 ELSE 2 END)
    + CASE WHEN importo_5x1000_2025 >= 100000 THEN 10
           WHEN importo_5x1000_2025 >= 10000 THEN 7
           WHEN importo_5x1000_2025 > 0 THEN 4 ELSE 0 END
    + CASE WHEN numero_appalti >= 10 THEN 8
           WHEN numero_appalti >= 5 THEN 6
           WHEN numero_appalti >= 1 THEN 3 ELSE 0 END
"""

FUNNEL_SQL_TEMPLATE = """
SELECT codice_fiscale, denominazione, comune, provincia, sezione,
       capacita_progettuale, importo_5x1000_2025, temi_anac,
       {MOTIVO} AS motivo_match,
       ROUND({SCORE}, 1) AS score
FROM '{ETS_FILE}'
WHERE {MATCH_COND}
  {GATE_SEZIONE}
  {GATE_TERRITORIO}
ORDER BY score DESC, importo_5x1000_2025 DESC NULLS LAST
LIMIT {LIMIT}
"""


def match_bando_funnel(con, tags, limit=10, territorio=None, testo=None):
    """Esegue il funnel completo e ritorna DataFrame con score."""
    gate_sez = gate_sezione(tags, testo)
    gate_terr = gate_territorio(territorio)
    match_cond, motivo_col = match_tema_sql(tags, testo)

    sql = (
        FUNNEL_SQL_TEMPLATE
        .replace("{MOTIVO}", motivo_col)
        .replace("{SCORE}", SCORE_SQL)
        .replace("{ETS_FILE}", str(ETS_FILE))
        .replace("{MATCH_COND}", match_cond)
        .replace("{GATE_SEZIONE}", gate_sez)
        .replace("{GATE_TERRITORIO}", gate_terr)
        .replace("{LIMIT}", str(limit))
    )
    return con.sql(sql).fetchdf()
