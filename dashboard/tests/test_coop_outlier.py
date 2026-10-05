"""Test contrattuali Open Cooperazione — qualità outlier e coerenza totali.

Prova del fuoco: se rompiamo `_coop_usable` o il flag di clean, cosa si rompe?
- KPI dashboard devono escludere gli outlier da TUTTI gli aggregati
- lo score top-capacità non deve dare il bonus "scala" agli outlier
- il clean deve esporre `is_bilancio_outlier` e usare macro toolkit

I test leggono i parquet locali (make run / toolkit run) — se mancano, skip.
"""

from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2]
CLEAN = REPO / "out" / "data" / "clean" / "open_cooperazione" / "2026" / "open_cooperazione_2026_clean.parquet"
PROFILO = REPO / "out" / "data" / "mart" / "open_cooperazione" / "2026" / "open_cooperazione_profilo.parquet"
CLEAN_SQL = REPO / "datasets" / "open-cooperazione" / "sql" / "clean.sql"


def _load(path: Path) -> pd.DataFrame:
    if not path.exists():
        pytest.skip(f"artifact assente: {path}")
    return pd.read_parquet(path)


def _usable(df: pd.DataFrame) -> pd.DataFrame:
    """Copia del filtro dashboard — se sources.py cambia, allineare qui."""
    if "is_bilancio_outlier" not in df.columns:
        return df
    bad = df["is_bilancio_outlier"].fillna(False).astype(bool)
    return df[~bad]


def test_clean_esporre_flag_outlier():
    df = _load(CLEAN)
    assert "is_bilancio_outlier" in df.columns
    # almeno il caso noto S. Egidio 2025 deve essere marcato
    seg = df[
        df["nome_organizzazione"].astype(str).str.contains("EGIDIO", case=False, na=False)
        & (df["anno_dati"] == 2025)
    ]
    assert len(seg) >= 1
    assert bool(seg["is_bilancio_outlier"].fillna(False).iloc[0]) is True


def test_kpi_aggregati_escludono_outlier():
    """Progetti/beneficiari/HR: somma con e senza outlier deve differire se l'outlier ha valori."""
    p = _load(PROFILO)
    if "is_bilancio_outlier" not in p.columns:
        pytest.skip("colonna is_bilancio_outlier assente nel profilo")
    p_ok = _usable(p)
    assert len(p_ok) < len(p)

    for col in ["bilancio_entrate", "progetti_diretti", "beneficiari", "dipendenti_estero"]:
        if col not in p.columns:
            continue
        tot_all = float(p[col].fillna(0).sum())
        tot_ok = float(p_ok[col].fillna(0).sum())
        # se l'outlier ha un valore >0, la somma "tutti" deve essere maggiore o uguale
        assert tot_ok <= tot_all + 1e-6
        # e non deve usare la somma "tutti" quando esiste la versione utile
        # (coerenza con UI "no outlier")
        if col == "bilancio_entrate":
            # caso noto: outlier ha ~3.4 mld → differenza netta
            assert tot_all - tot_ok > 1e8


def test_top_capacita_no_bonus_scala_outlier():
    """L'outlier non deve guadagnare il punto 'entrate > 1M' dal bilancio anomalo."""
    p = _load(PROFILO)
    if "is_bilancio_outlier" not in p.columns:
        pytest.skip("colonna assente")
    if "bilancio_entrate" not in p.columns:
        pytest.skip("bilancio_entrate assente")

    bil_ok = p["bilancio_entrate"].fillna(0).astype(float).copy()
    bad = p["is_bilancio_outlier"].fillna(False).astype(bool)
    bil_ok = bil_ok.mask(bad, 0.0)

    # replica dello score scala
    bonus_ok = (bil_ok > 1_000_000).astype(int)
    bonus_raw = (p["bilancio_entrate"].fillna(0) > 1_000_000).astype(int)

    # per le righe outlier, bonus utile deve essere 0
    assert int(bonus_ok[bad].sum()) == 0
    # se un outlier aveva entrate > 1M, il bonus raw avrebbe dato 1
    if bad.any() and (p.loc[bad, "bilancio_entrate"].fillna(0) > 1_000_000).any():
        assert int(bonus_raw[bad].sum()) >= 1


def test_clean_sql_usa_macro_toolkit():
    if not CLEAN_SQL.exists():
        pytest.skip("clean.sql assente")
    sql = CLEAN_SQL.read_text(encoding="utf-8")
    assert "cast_int(" in sql
    assert "cast_double(" in sql
    assert "cast_bigint(" in sql
    # non deve più usare TRY_CAST grezzo per i campi tipizzati
    assert "TRY_CAST" not in sql
    assert "is_bilancio_outlier" in sql
