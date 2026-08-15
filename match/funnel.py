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
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))

from lib.config import ETS_FILE, get_province_filter
from lib.temi import TEMA_PATTERN, estrai_temi, normalizza_tags, sezioni_per_tag, tema_principale


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


# Temi dove la SEZIONE RUNTS è ammessa di per sé (GATE, non match pieno):
# un'ODV è per definizione un'organizzazione di volontariato — entra nel
# bando, ma lo score pieno spetta a chi conferma il tema nel nome/temi.
# La sezione ammette (gate), non premia (match). Evita il bias per cui
# TUTTE le 70k APS matchano ogni bando sport solo per essere APS.
SEZIONE_AS_TEMA: dict[str, str] = {
    "volontariato": "ORGANIZZAZIONI DI VOLONTARIATO",
    "sport": "ASSOCIAZIONI DI PROMOZIONE SOCIALE",
}


def match_tema_sql(tags, testo=None):
    """Costruisce le condizioni SQL di pertinenza (2 assi).

    ASSE 1 — IDONEITÀ (filtro duro, vedi gate_sezione/territorio):
      chi è ammesso dal tema principale. La sezione-as-tema è un GATE,
      non un match principale.

    ASSE 2 — PERTINENZA (score continuo, non sì/no):
      - match sul TEMA PRINCIPALE vale 2 (FORTE)
      - ogni altro tag del bando matchato vale 1 (MEDIO) — così bandi
        multi-tag producono liste diverse (fix selettività)
      - SOLO sezione (ODV=volontariato, APS=sport): debole — ammette
        ma non premia chi è solo di quella sezione senza conferma nel nome

    Ritorna dict con:
      - cond: condizione di ammissione (OR di tutto)
      - motivo: motivo_match per leggibilità
      - n_match: espressione SQL = conteggio tag matchati (prim=2, sec=1)
    """
    tema_prim = tema_principale(tags, testo)
    pattern_prim = TEMA_PATTERN.get(tema_prim) if tema_prim else None
    sez_prim = SEZIONE_AS_TEMA.get(tema_prim) if tema_prim else None

    normalizzati = normalizza_tags(tags)
    if not normalizzati and testo:
        normalizzati = estrai_temi(testo)

    # Condizione per OGNI tag normalizzato (non solo il principale)
    cond_by_tag: dict[str, str] = {}
    for t in normalizzati:
        p = TEMA_PATTERN.get(t)
        if p:
            cond_by_tag[t] = _cond(p)

    prim_denom = cond_by_tag.get(tema_prim) if tema_prim else None
    sec_conds = [c for t, c in cond_by_tag.items() if t != tema_prim]

    sez_cond = f"sezione = '{sez_prim}'" if sez_prim else None

    # Condizione di ammissione: nome matcha un qualunque tag, OPPURE
    # sezione-as-tema. (temi_anac rimosso dal matching: copertura 5%,
    # boost marginale — il nome del tema è sufficiente.)
    cond_parts = [p for p in (prim_denom, *sec_conds, sez_cond) if p]
    cond = "(" + " OR ".join(cond_parts) + ")" if cond_parts else "1=0"

    whens = []
    if prim_denom:
        whens.append(f"WHEN {prim_denom} THEN 'tema_principale'")
    if sec_conds:
        whens.append(f"WHEN ({' OR '.join(sec_conds)}) THEN 'tema_secondario'")
    if sez_cond:
        whens.append(f"WHEN {sez_cond} THEN 'solo_sezione'")
    motivo = "CASE " + " ".join(whens) + " ELSE NULL END"

    # n_match: tema principale vale 2, ogni altro tag 1
    n_match_parts = []
    if prim_denom:
        n_match_parts.append(f"(CASE WHEN {prim_denom} THEN 2 ELSE 0 END)")
    for c in sec_conds:
        n_match_parts.append(f"(CASE WHEN {c} THEN 1 ELSE 0 END)")
    n_match = " + ".join(n_match_parts) if n_match_parts else "0"

    return {"cond": cond, "motivo": motivo, "n_match": n_match}


# ── Stage 3: ranking (pertinenza × capacità) ───────────────────────

# La capacità è un MOLTIPLICATORE della pertinenza (0-30%), non un addendo:
# un ETS con tema esatto e capacità media batte un gigante generico.
CAP_FACTOR_SQL = """
    (CASE capacita_progettuale
        WHEN 'alta' THEN 0.30 WHEN 'medio-alta' THEN 0.20
        WHEN 'media' THEN 0.10 WHEN 'base' THEN 0.05 ELSE 0.0 END)
"""

# Bonus 5x1000 come addendo MINORE (non deve dominare la pertinenza).
X1000_BONUS_SQL = """
    CASE WHEN importo_5x1000_2025 >= 100000 THEN 8
         WHEN importo_5x1000_2025 >= 10000 THEN 5
         WHEN importo_5x1000_2025 > 0 THEN 2 ELSE 0 END
"""


def _build_score_sql(n_match_sql: str) -> str:
    """Score = pertinenza (n_match×60) × (1+capacità) + bonus 5x1000."""
    return (
        f"ROUND((({n_match_sql}) * 60) * (1 + {CAP_FACTOR_SQL})"
        f" + {X1000_BONUS_SQL}, 1)"
    )


FUNNEL_SQL_TEMPLATE = """
SELECT codice_fiscale, denominazione, comune, provincia, sezione,
       capacita_progettuale, importo_5x1000_2025,
       {MOTIVO} AS motivo_match,
       {SCORE} AS score
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
    parts = match_tema_sql(tags, testo)
    score_sql = _build_score_sql(parts["n_match"])

    sql = (
        FUNNEL_SQL_TEMPLATE
        .replace("{MOTIVO}", parts["motivo"])
        .replace("{SCORE}", score_sql)
        .replace("{ETS_FILE}", str(ETS_FILE))
        .replace("{MATCH_COND}", parts["cond"])
        .replace("{GATE_SEZIONE}", gate_sez)
        .replace("{GATE_TERRITORIO}", gate_terr)
        .replace("{LIMIT}", str(limit))
    )
    return con.sql(sql).fetchdf()


# ── Incrocio territoriale: match ETS × contesto comune ─────────────

COMUNI_ETS_FILE = ROOT / "data" / "comuni_ets.parquet"


def match_territoriale(con, tags, limit=200, territorio=None, testo=None, top_comuni=10):
    """Incrocia i match ETS con il contesto socio-economico del comune.

    Ritorna (match_con_contesto, gap_comuni):
      - match_con_contesto: ogni ETS matchato + reddito/RdC/sport del suo comune
      - gap_comuni: comuni ordinati per 'bisogno' (ETS matchabili bassi vs
        contesto fragile: RdC alto, reddito basso)
    """
    df = match_bando_funnel(con, tags, limit=limit, territorio=territorio, testo=testo)
    if df.empty:
        return df, con.sql(
            f"SELECT comune, provincia, rd_pct, reddito_procapite, ets_tot, ets_matchabili "
            f"FROM '{COMUNI_ETS_FILE}' ORDER BY rd_pct DESC LIMIT {top_comuni}"
        ).fetchdf()

    # 1. Match + contesto del comune (JOIN normalizzato su comune+provincia)
    match_ctx = con.sql(f"""
        SELECT e.codice_fiscale, e.denominazione, e.comune, e.provincia,
               e.motivo_match, e.score, e.capacita_progettuale,
               c.reddito_procapite, c.rd_pct, c.ets_tot, c.ets_matchabili,
               c.sport AS sport_comune, c.popolazione
        FROM df e
        LEFT JOIN '{COMUNI_ETS_FILE}' c
          ON lower(e.comune) = lower(c.comune) AND e.provincia = c.provincia
        ORDER BY e.score DESC
    """).fetchdf()

    # 2. Gap: comuni del territorio con contesto fragile ma pochi ETS matchabili
    if territorio:
        prov = get_province_filter(territorio)
        prov_sql = ""
        if prov:
            quote = ", ".join(f"'{p}'" for p in prov)
            prov_sql = f"AND provincia IN ({quote})"
        gap = con.sql(f"""
            SELECT comune, provincia, rd_pct, reddito_procapite,
                   ets_tot, ets_matchabili, capacita_alta, sport,
                   siope_uscite, siope_personale, pnrr_progetti,
                   ROUND(ets_matchabili * 1.0 / GREATEST(ets_tot, 1), 2) AS quota_matchabile
            FROM '{COMUNI_ETS_FILE}'
            WHERE 1=1 {prov_sql}
              AND ets_tot > 0
            ORDER BY rd_pct DESC, ets_matchabili ASC
            LIMIT {top_comuni}
        """).fetchdf()
    else:
        gap = con.sql(f"""
            SELECT comune, provincia, rd_pct, reddito_procapite,
                   ets_tot, ets_matchabili, capacita_alta, sport,
                   siope_uscite, siope_personale, pnrr_progetti,
                   ROUND(ets_matchabili * 1.0 / GREATEST(ets_tot, 1), 2) AS quota_matchabile
            FROM '{COMUNI_ETS_FILE}'
            WHERE ets_tot > 0
            ORDER BY rd_pct DESC, ets_matchabili ASC
            LIMIT {top_comuni}
        """).fetchdf()

    return match_ctx, gap


def format_incrocio(match_ctx, gap, titolo="Incrocio territoriale"):
    """Render testuale dell'incrocio (per report/shell)."""
    lines = [f"# 🌍 {titolo}", ""]
    if match_ctx.empty:
        lines.append("_Nessun ETS matchato._")
        return "\n".join(lines)

    lines.append(f"## ETS matchati con contesto comune ({len(match_ctx)})")
    lines.append("")
    lines.append("| ETS | Comune | Score | Reddito | RdC% | Sport nel comune |")
    lines.append("|---|---|---|---|---|---|")
    for _, r in match_ctx.head(15).iterrows():
        reddito = f"{r['reddito_procapite']:,}" if r["reddito_procapite"] else "—"
        rdc = f"{r['rd_pct']}%" if r["rd_pct"] is not None else "—"
        sport = str(r["sport_comune"]) if r["sport_comune"] is not None else "—"
        lines.append(f"| {r['denominazione'][:35]} | {r['comune']} ({r['provincia']}) "
                     f"| {r['score']} | {reddito} | {rdc} | {sport} |")

    lines.append("")
    lines.append("## Gap: comuni con contesto fragile e pochi ETS matchabili")
    lines.append("")
    lines.append("| Comune | Prov | RdC% | Reddito | ETS tot | Matchabili | Quota | Spesa SIOPE | PNRR proj |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for _, r in gap.head(15).iterrows():
        siope = f"{r['siope_uscite']/1e6:.0f}M€" if r["siope_uscite"] and r["siope_uscite"] > 0 else "—"
        pnrr = str(int(r["pnrr_progetti"])) if r["pnrr_progetti"] and r["pnrr_progetti"] > 0 else "—"
        lines.append(f"| {r['comune']} | {r['provincia']} | {r['rd_pct']}% | "
                     f"{r['reddito_procapite']:,} | {r['ets_tot']} | {r['ets_matchabili']} "
                     f"| {r['quota_matchabile']} | {siope} | {pnrr} |")

    return "\n".join(lines)
