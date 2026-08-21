"""Display formatting utilities for match results."""

import math
import re
from datetime import date, datetime

from config import MESI_IT


def parse_date_flex(s):
    oggi = date.today()
    if not s:
        return None, 999
    s = s.strip().lower()
    m = re.match(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})", s)
    if m:
        giorno, mese, anno = m.groups()
        mese_num = MESI_IT.get(mese)
        if mese_num:
            try:
                d = date(int(anno), int(mese_num), int(giorno))
                return d, (d - oggi).days
            except ValueError:
                pass
    try:
        d = datetime.strptime(s, "%d/%m/%Y").date()
        return d, (d - oggi).days
    except ValueError:
        pass
    return None, 999


def is_missing(value):
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).lower() == "nan"


def fmt_text(value, default="-"):
    return default if is_missing(value) else str(value)


def fmt_euro(value):
    if is_missing(value):
        return "-"
    return f"€{value:,.0f}"


def fmt_tags(tags):
    return ", ".join(tags) if tags else "-"


def fmt_match_reason(c):
    motivo = c.get("motivo_match", "match")
    motivo_map = {
        "tema+sport+sezione": "match tema + sport + sezione",
        "tema+sport": "match tema + sport",
        "tema+sezione": "match tema + sezione",
        "tema denominazione": "match su denominazione",
        "sport da denominazione": "sport da denominazione",
        "sezione": "match su sezione",
        "solo_sezione": "solo per sezione (nessuna conferma nel nome)",
        "match": "match",
    }
    parts = [motivo_map.get(motivo, motivo)]
    cap = c.get("capacita_progettuale")
    if cap:
        parts.append(f"capacità {cap}")
    cinque = c.get("importo_5x1000_2025")
    if not is_missing(cinque):
        if cinque >= 100000:
            parts.append("5x1000 >100k")
        elif cinque >= 10000:
            parts.append("5x1000 >10k")
        elif cinque > 0:
            parts.append("5x1000 presente")
    if c.get("ha_finanziamenti_ue") is True:
        parts.append("grant UE")
    if c.get("ha_progetti_pnrr") is True:
        parts.append("PNRR")
    sez = c.get("sezione")
    if sez == "IMPRESE SOCIALI":
        parts.append("Impresa Sociale")
    elif sez == "ORGANIZZAZIONI DI VOLONTARIATO":
        parts.append("ODV")
    elif sez == "ASSOCIAZIONI DI PROMOZIONE SOCIALE":
        parts.append("APS")
    if c.get("ha_appalti_pubblici") is True:
        imp = c.get("importo_appalti", 0)
        if not is_missing(imp) and imp >= 1000000:
            parts.append(f"appalti €{imp:,.0f}")
        else:
            parts.append("appalti pubblici")
    return "; ".join(parts)
