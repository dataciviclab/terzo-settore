#!/usr/bin/env python3
"""Download + preprocessing Open Cooperazione (OSC cooperazione allo sviluppo).

Fonte: https://www.open-cooperazione.it — progetto Info-Cooperazione.
Licenza sito: CC BY 3.0 IT. CSV annuale autodichiarato dalle organizzazioni.

Il download e' un flusso ASP.NET WebForms:
  1. GET su Scarica-Dati.aspx per VIEWSTATE / VIEWSTATEGENERATOR / EVENTVALIDATION
  2. POST con __EVENTTARGET = _pulsante_scarica_dati$LK_DOWNLOAD
  3. Risposta application/octet-stream (CSV latin-1, separatore ';')

Preprocessing (servito perché il raw e' ostile al lettore toolkit):
  - encoding latin-1, campi multi-riga quotati, ';' come separatore
  - header duplicati (Anno x3, Modalita x2) e colonna coda vuota
  - numeri in formato italiano (1.234,56)
  - manca il codice fiscale → join su data/cf_mapping.csv (scrape schede)
  - flag testuali SI/NO e date libere

Output: CSV UTF-8 snake_case (raw_input per clean.sql).

Uso:
    python scripts/fetch_open_cooperazione.py --output raw_input.csv
    python scripts/fetch_open_cooperazione.py --output raw_input.csv --force
    python scripts/fetch_open_cooperazione.py --output raw_input.csv --skip-download
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

BASE_URL = "https://www.open-cooperazione.it"
DOWNLOAD_URL = f"{BASE_URL}/web/Scarica-Dati.aspx"
EVENT_TARGET = "_pulsante_scarica_dati$LK_DOWNLOAD"
MIN_SIZE = 500_000

DATASET_DIR = Path(__file__).resolve().parents[1]
CF_MAPPING_PATH = DATASET_DIR / "data" / "cf_mapping.csv"
CACHE_DIR = DATASET_DIR / "data" / "raw_cache"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
    "Referer": DOWNLOAD_URL,
}

# Colonne raw (ordine header originale, posizioni stabili da CSV ufficiale)
_RAW_HEADER = [
    "Anno", "Nome organizzazione", "Indirizzo", "Città", "Provincia", "CAP",
    "Email organizzazione", "Telefono", "Anno fondazione", "Forma giuritica",
    "ETS DLGS 117-2017", "Iscritto elenco AICS",
    "Reti di rappresentanza e Federazioni", "Sitoweb",
    "Facebook", "X", "Linkedin", "Instagram",
    "Obiettivi Sviluppo Sostenibile SDGs",
    "Rappresentante nome", "Rappresentante cognome", "Rappresentante sesso",
    "Rappresentante anno in carica",
    "Segretario nome", "Segretario cognome", "Segretario sesso",
    "Segretario anno in carica",
    "Composizione direttivo",
    "Numero associati", "Numero associati Uomini", "Numero associati Donne",
    "Numero associati (Organizzazioni)",
    "Organo di controllo interno", "Status Ecosoc Nazioni Unite",
    "Compliance_231_2001", "Certificazioni",
    "Partenariati organizzazioni", "Partenariati_con_aziende",
    "Partenariati_con_Enti_Pubblici",
    "Codice etico", "Organigramma", "Pianificazione strategica",
    # blocco bilancio (Anno duplicato)
    "Anno", "Bilancio tot. Entrate", "Bilancio tot. Uscite",
    "Modalita redazione bilancio", "Principio OIC35", "Bilancio certificato",
    "Modalita di redazione bilancio", "Oss. principio contabile OIC35",
    "Oneri missione", "Oneri struttura", "Oneri raccolta fondi",
    "Numero_donatori",
    "Fondi donatori istituzionali", "Fondi donatori privati",
    "Fondi da Aziende", "Fondi  da Fondazioni", "Fondi da Chiese",
    "Elenco_contributi_pubblici_incassati",
    "Principali_donatori_Aziende", "Principali_donatori_Fondazioni",
    "Principali_donatori_Istituzioni",
    "Fondi 5x1000", "Numero firme 5x1000",
    "Adozioni distanza", "Numero Adozioni attive",
    "Principali finanziatori pubblici",
    "Bilancio economico", "Certificazione bilancio",
    "Relazione di missione", "Relazione controllo",
    # blocco risorse umane (ANNO duplicato)
    "ANNO",
    "Dipendenti Indeterminati Maschi Italia",
    "Dipendenti Indeterminati Femmine Italia",
    "Dipendenti Determinati Maschi Italia",
    "Dipendenti Determinati Femmine Italia",
    "Collaboratori co.co.co Maschi Italia",
    "Collaboratori co.co.co Femmine Italia",
    "Consulenti PIVA Maschi Italia",
    "Consulenti PIVA Femmine Italia",
    "Espatriati Indeterminati Maschi Estero",
    "Espatriati Indeterminati Femmine Estero",
    "Espatriati Determinati Maschi Estero",
    "Espatriati Determinati Femmine Estero",
    "Espatriati occasionale Maschi Estero",
    "Espatriati occasionale  Femmine Estero",
    "Espatriati OSC Maschio Estero",
    "Espatriati OSC Femmine Estero",
    "Espatriati Consulenti PIVA Maschi Estero",
    "Espatriati Consulenti PIVA Femmine Estero",
    "Dipendenti Contratti Locali Maschi Estero",
    "Dipendenti Contratti Locali Femmine Estero",
    "Retribuzione più alta", "Retribuzione più bassa", "Retribuzione direttivo",
    "Retribuzione più alta estero", "Retribuzione più bassa estero",
    "Iscrizione_Fondi_interprofessionali",
    "Numero Volontari Servizio Civile", "Numero Volontari Totale Attivi",
    "Numero di progetti sostenuti direttamente",
    "Numero di progetti sostenuti indirettamente",
    "Beneficiari diretti indiretti",
    "Bilancio sociale", "Valutazione impatto",
    "Stato anagrafica", "Approvazione", "Stato dati annuale",
]

# Mappa nome_raw -> nome_output (gestisce duplicati per posizione)
_COL_BY_INDEX = {
    0: "anno_dati",
    1: "nome_organizzazione",
    2: "indirizzo",
    3: "citta",
    4: "provincia",
    5: "cap",
    6: "email",
    7: "telefono",
    8: "anno_fondazione",
    9: "forma_giuridica",
    10: "is_ets",
    11: "is_aics",
    12: "reti",
    13: "sitoweb",
    14: "facebook",
    15: "x",
    16: "linkedin",
    17: "instagram",
    18: "sdgs",
    19: "rappresentante_nome",
    20: "rappresentante_cognome",
    21: "rappresentante_sesso",
    22: "rappresentante_anno_in_carica",
    23: "segretario_nome",
    24: "segretario_cognome",
    25: "segretario_sesso",
    26: "segretario_anno_in_carica",
    27: "composizione_direttivo",
    28: "numero_associati",
    29: "numero_associati_uomini",
    30: "numero_associati_donne",
    31: "numero_associati_organizzazioni",
    32: "organo_controllo_interno",
    33: "ecosoc",
    34: "compliance_231",
    35: "certificazioni",
    36: "partenariati_organizzazioni",
    37: "partenariati_aziende",
    38: "partenariati_enti_pubblici",
    39: "codice_etico",
    40: "organigramma",
    41: "pianificazione_strategica",
    42: "anno_bilancio",
    43: "bilancio_entrate",
    44: "bilancio_uscite",
    45: "modalita_redazione_bilancio",
    46: "principio_oic35",
    47: "bilancio_certificato",
    48: "modalita_redazione_bilancio_2",
    49: "oss_principio_oic35",
    50: "oneri_missione",
    51: "oneri_struttura",
    52: "oneri_raccolta_fondi",
    53: "numero_donatori",
    54: "fondi_istituzionali",
    55: "fondi_privati",
    56: "fondi_aziende",
    57: "fondi_fondazioni",
    58: "fondi_chiese",
    59: "contributi_pubblici_url",
    60: "principali_donatori_aziende",
    61: "principali_donatori_fondazioni",
    62: "principali_donatori_istituzioni",
    63: "fondi_5x1000",
    64: "firme_5x1000",
    65: "adozioni_distanza",
    66: "numero_adozioni_attive",
    67: "principali_finanziatori_pubblici",
    68: "bilancio_economico",
    69: "certificazione_bilancio",
    70: "relazione_missione",
    71: "relazione_controllo",
    72: "anno_risorse_umane",
    73: "dip_ind_m_italia",
    74: "dip_ind_f_italia",
    75: "dip_det_m_italia",
    76: "dip_det_f_italia",
    77: "coco_m_italia",
    78: "coco_f_italia",
    79: "piva_m_italia",
    80: "piva_f_italia",
    81: "esp_ind_m_estero",
    82: "esp_ind_f_estero",
    83: "esp_det_m_estero",
    84: "esp_det_f_estero",
    85: "esp_occ_m_estero",
    86: "esp_occ_f_estero",
    87: "esp_osc_m_estero",
    88: "esp_osc_f_estero",
    89: "esp_piva_m_estero",
    90: "esp_piva_f_estero",
    91: "loc_m_estero",
    92: "loc_f_estero",
    93: "retribuzione_piu_alta",
    94: "retribuzione_piu_bassa",
    95: "retribuzione_direttivo",
    96: "retribuzione_piu_alta_estero",
    97: "retribuzione_piu_bassa_estero",
    98: "fondi_interprofessionali",
    99: "volontari_servizio_civile",
    100: "volontari_totali",
    101: "progetti_diretti",
    102: "progetti_indiretti",
    103: "beneficiari",
    104: "bilancio_sociale",
    105: "valutazione_impatto",
    106: "stato_anagrafica",
    107: "approvazione",
    108: "stato_dati_annuale",
}

_OUTPUT_COLS = [
    "codice_fiscale",
    "nome_organizzazione",
    "url_scheda",
    "anno_dati",
    "anno_bilancio",
    "anno_risorse_umane",
    "indirizzo",
    "citta",
    "provincia",
    "cap",
    "email",
    "telefono",
    "anno_fondazione",
    "forma_giuridica",
    "is_ets",
    "is_aics",
    "reti",
    "sitoweb",
    "sdgs",
    "rappresentante_nome",
    "rappresentante_cognome",
    "rappresentante_sesso",
    "rappresentante_anno_in_carica",
    "segretario_nome",
    "segretario_cognome",
    "numero_associati",
    "organo_controllo_interno",
    "ecosoc",
    "compliance_231",
    "certificazioni",
    "partenariati_enti_pubblici",
    "codice_etico",
    "pianificazione_strategica",
    "bilancio_entrate",
    "bilancio_uscite",
    "bilancio_certificato",
    "oneri_missione",
    "oneri_struttura",
    "oneri_raccolta_fondi",
    "numero_donatori",
    "fondi_istituzionali",
    "fondi_privati",
    "fondi_aziende",
    "fondi_fondazioni",
    "fondi_chiese",
    "fondi_5x1000",
    "firme_5x1000",
    "adozioni_distanza",
    "numero_adozioni_attive",
    "principali_finanziatori_pubblici",
    "bilancio_sociale",
    "valutazione_impatto",
    "dipendenti_italia",
    "dipendenti_estero",
    "volontari_servizio_civile",
    "volontari_totali",
    "progetti_diretti",
    "progetti_indiretti",
    "beneficiari",
    "stato_dati_annuale",
]

_ITALIAN_NUM_RE = re.compile(r"^\s*-?\d{1,3}(?:\.\d{3})*(?:,\d+)?\s*$|^\s*-?\d+(?:,\d+)?\s*$")


def _extract_token(html: str, name: str) -> str:
    m = re.search(rf'name="{name}"\s+id="{name}"\s+value="([^"]*)"', html)
    if not m:
        m = re.search(rf'id="{name}"\s+name="{name}"\s+value="([^"]*)"', html)
    if not m:
        raise RuntimeError(f"Token ASP.NET '{name}' non trovato")
    return m.group(1)


def download_csv() -> bytes:
    session = requests.Session()
    session.headers.update(HEADERS)

    r = session.get(DOWNLOAD_URL, timeout=30)
    r.raise_for_status()
    html = r.text

    data = {
        "__EVENTTARGET": EVENT_TARGET,
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": _extract_token(html, "__VIEWSTATE"),
        "__VIEWSTATEGENERATOR": _extract_token(html, "__VIEWSTATEGENERATOR"),
        "__EVENTVALIDATION": _extract_token(html, "__EVENTVALIDATION"),
    }
    r2 = session.post(DOWNLOAD_URL, data=data, timeout=90, allow_redirects=True)
    r2.raise_for_status()

    ct = r2.headers.get("content-type", "")
    cd = r2.headers.get("content-disposition", "")
    if "octet-stream" not in ct and "csv" not in ct.lower() and "attachment" not in cd.lower():
        raise RuntimeError(
            f"Risposta non CSV: content-type={ct!r} disposition={cd!r} size={len(r2.content)}"
        )
    if len(r2.content) < MIN_SIZE:
        raise RuntimeError(f"CSV troppo piccolo: {len(r2.content)} bytes")
    return r2.content


def load_cf_mapping() -> dict[str, dict]:
    if not CF_MAPPING_PATH.exists():
        raise RuntimeError(f"CF mapping mancante: {CF_MAPPING_PATH}")
    with CF_MAPPING_PATH.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        by_name: dict[str, dict] = {}
        by_cf: dict[str, dict] = {}
        for row in reader:
            cf = (row.get("codice_fiscale") or "").strip()
            nome_norm = (row.get("nome_norm") or "").strip()
            rec = {
                "codice_fiscale": cf,
                "url_scheda": (row.get("url_scheda") or "").strip(),
            }
            if cf:
                by_cf.setdefault(cf, rec)
            if nome_norm:
                by_name.setdefault(nome_norm, rec)
    return {"by_name": by_name, "by_cf": by_cf}


def norm_name(s: str) -> str:
    s = (s or "").upper()
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    s = re.sub(
        r"\b(ETS|ODV|APS|ONLUS|FONDAZIONE|ASSOCIAZIONE|ENTE|SOCIETA|ONG|DI MUTUO SOCCORSO)\b",
        " ",
        s,
    )
    return re.sub(r"\s+", " ", s).strip()


def parse_italian_number(raw: str) -> str:
    """'1.234,56' -> '1234.56'; vuoto/invalide -> ''. Ritorna stringa per CSV."""
    if raw is None:
        return ""
    s = str(raw).strip().replace(" ", " ").replace(" ", "")
    if not s or s in {"-", "n.d.", "N.D.", "NA", "N/A"}:
        return ""
    # percentuale "86.10%" -> solo numero
    s = s.replace("%", "")
    if not s:
        return ""
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    if not _ITALIAN_NUM_RE.match(s if not neg else s):
        # tentativo diretto
        try:
            float(s.replace(".", "").replace(",", "."))
        except ValueError:
            return ""
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif s.count(".") > 1 or (s.count(".") == 1 and len(s.split(".")[1]) == 3 and len(s.split(".")[0]) <= 3):
        # 1.234 o 1.234.567 -> rimuovi punti migliaia
        parts = s.split(".")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            s = "".join(parts)
    try:
        val = float(s)
    except ValueError:
        return ""
    if neg:
        val = -val
    # normalizza output: niente code scientifiche inutili
    if val == int(val) and abs(val) < 1e15:
        return str(int(val))
    return repr(val)


def parse_intish(raw: str) -> str:
    n = parse_italian_number(raw)
    if not n:
        return ""
    try:
        return str(int(float(n)))
    except ValueError:
        return ""


def clean_flag(raw: str) -> str:
    s = (raw or "").strip().upper()
    if s in {"SI", "SÌ", "S", "YES", "Y", "TRUE"}:
        return "SI"
    if s in {"NO", "N", "FALSE"}:
        return "NO"
    return ""


def row_get(row: list[str], idx: int) -> str:
    if idx < len(row):
        return (row[idx] or "").strip()
    return ""


def preprocess(raw_bytes: bytes, mapping: dict) -> tuple[list[dict], dict]:
    text = raw_bytes.decode("latin-1")
    reader = csv.reader(io.StringIO(text), delimiter=";", quotechar='"')
    rows = list(reader)
    if not rows:
        raise RuntimeError("CSV vuoto")

    header = rows[0]
    n_header = len(header)
    stats = {
        "raw_rows": len(rows) - 1,
        "bad_field_count": 0,
        "matched_cf": 0,
        "unmatched": 0,
        "years": {},
    }

    out_rows: list[dict] = []
    for row in rows[1:]:
        if not row or not any(c.strip() for c in row):
            continue
        # righe corrotte: troppo poche colonne e non riparabili
        if len(row) < 20:
            stats["bad_field_count"] += 1
            continue
        # allinea a header: se lunghezza diversa, tronca/estendi
        if len(row) < n_header:
            row = row + [""] * (n_header - len(row))
        elif len(row) > n_header:
            # conserva prime n_header colonne note; l'eccedenza e' free-text malformato
            row = row[:n_header]

        rec: dict[str, str] = {c: "" for c in _OUTPUT_COLS}

        nome = row_get(row, 1)
        if not nome:
            continue

        anno = row_get(row, 0)
        # righe corrotte del raw: nome/anno non validi (es. residuo di campo multi-riga)
        if not re.fullmatch(r"\d{4}", anno or ""):
            stats["bad_field_count"] += 1
            continue
        if len(nome) < 3 or not re.search(r"[A-Za-zÀ-ÿ]", nome):
            stats["bad_field_count"] += 1
            continue

        rec["nome_organizzazione"] = nome
        rec["anno_dati"] = anno
        rec["anno_bilancio"] = row_get(row, 42)
        rec["anno_risorse_umane"] = row_get(row, 72)

        # join CF
        key = norm_name(nome)
        hit = mapping["by_name"].get(key)
        if not hit:
            # fallback: match parziale su prime parole
            parts = key.split()
            if len(parts) >= 2:
                pref = " ".join(parts[:3])
                for k, v in mapping["by_name"].items():
                    if k.startswith(pref) or pref.startswith(k[: len(pref)]):
                        hit = v
                        break
        if hit:
            rec["codice_fiscale"] = hit["codice_fiscale"]
            rec["url_scheda"] = hit["url_scheda"]
            stats["matched_cf"] += 1
        else:
            stats["unmatched"] += 1

        for idx, col in _COL_BY_INDEX.items():
            if col in rec or col.startswith("dip_") or col.startswith("coco_") or col.startswith("piva_") or col.startswith("esp_") or col.startswith("loc_"):
                pass
        # campi testuali
        rec["indirizzo"] = row_get(row, 2)
        rec["citta"] = row_get(row, 3)
        rec["provincia"] = row_get(row, 4).upper()
        rec["cap"] = row_get(row, 5)
        rec["email"] = row_get(row, 6)
        rec["telefono"] = row_get(row, 7)
        rec["anno_fondazione"] = row_get(row, 8)
        rec["forma_giuridica"] = row_get(row, 9)
        rec["is_ets"] = clean_flag(row_get(row, 10))
        rec["is_aics"] = clean_flag(row_get(row, 11))
        rec["reti"] = row_get(row, 12)
        rec["sitoweb"] = row_get(row, 13)
        rec["sdgs"] = row_get(row, 18)
        rec["rappresentante_nome"] = row_get(row, 19)
        rec["rappresentante_cognome"] = row_get(row, 20)
        rec["rappresentante_sesso"] = row_get(row, 21).upper()
        rec["rappresentante_anno_in_carica"] = row_get(row, 22)
        rec["segretario_nome"] = row_get(row, 23)
        rec["segretario_cognome"] = row_get(row, 24)
        rec["numero_associati"] = parse_intish(row_get(row, 28))
        rec["organo_controllo_interno"] = clean_flag(row_get(row, 32))
        rec["ecosoc"] = clean_flag(row_get(row, 33))
        rec["compliance_231"] = clean_flag(row_get(row, 34))
        rec["certificazioni"] = row_get(row, 35)
        rec["partenariati_enti_pubblici"] = row_get(row, 38)
        rec["codice_etico"] = clean_flag(row_get(row, 39))
        rec["pianificazione_strategica"] = clean_flag(row_get(row, 41))

        # bilancio / fondi
        rec["bilancio_entrate"] = parse_italian_number(row_get(row, 43))
        rec["bilancio_uscite"] = parse_italian_number(row_get(row, 44))
        rec["bilancio_certificato"] = clean_flag(row_get(row, 47))
        rec["oneri_missione"] = parse_italian_number(row_get(row, 50))
        rec["oneri_struttura"] = parse_italian_number(row_get(row, 51))
        rec["oneri_raccolta_fondi"] = parse_italian_number(row_get(row, 52))
        rec["numero_donatori"] = parse_intish(row_get(row, 53))
        rec["fondi_istituzionali"] = parse_italian_number(row_get(row, 54))
        rec["fondi_privati"] = parse_italian_number(row_get(row, 55))
        rec["fondi_aziende"] = parse_italian_number(row_get(row, 56))
        rec["fondi_fondazioni"] = parse_italian_number(row_get(row, 57))
        rec["fondi_chiese"] = parse_italian_number(row_get(row, 58))
        rec["fondi_5x1000"] = parse_italian_number(row_get(row, 63))
        rec["firme_5x1000"] = parse_intish(row_get(row, 64))
        rec["adozioni_distanza"] = clean_flag(row_get(row, 65))
        rec["numero_adozioni_attive"] = parse_intish(row_get(row, 66))
        rec["principali_finanziatori_pubblici"] = row_get(row, 67)
        rec["bilancio_sociale"] = clean_flag(row_get(row, 104))
        rec["valutazione_impatto"] = clean_flag(row_get(row, 105))

        # HR aggregate
        italia_idx = [73, 74, 75, 76, 77, 78, 79, 80]
        estero_idx = [81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92]
        dip_it = 0
        for i in italia_idx:
            v = parse_intish(row_get(row, i))
            if v:
                dip_it += int(v)
        dip_es = 0
        for i in estero_idx:
            v = parse_intish(row_get(row, i))
            if v:
                dip_es += int(v)
        rec["dipendenti_italia"] = str(dip_it)
        rec["dipendenti_estero"] = str(dip_es)

        rec["volontari_servizio_civile"] = parse_intish(row_get(row, 99))
        rec["volontari_totali"] = parse_intish(row_get(row, 100))
        rec["progetti_diretti"] = parse_intish(row_get(row, 101))
        rec["progetti_indiretti"] = parse_intish(row_get(row, 102))
        rec["beneficiari"] = parse_intish(row_get(row, 103))
        rec["stato_dati_annuale"] = row_get(row, 108)

        if anno:
            stats["years"][anno] = stats["years"].get(anno, 0) + 1
        out_rows.append(rec)

    return out_rows, stats


def write_csv(rows: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        # stesso dialetto della fonte e di ade-cinque-per-mille: ';' + quote
        w = csv.DictWriter(
            f,
            fieldnames=_OUTPUT_COLS,
            extrasaction="ignore",
            delimiter=";",
            quotechar='"',
            quoting=csv.QUOTE_MINIMAL,
        )
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in _OUTPUT_COLS})


def main() -> int:
    parser = argparse.ArgumentParser(description="Open Cooperazione: download CSV + preprocessing")
    parser.add_argument("--output", required=True, help="path CSV tidy di output (raw_input)")
    parser.add_argument("--force", action="store_true", help="ignora cache raw del giorno")
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="usa cache locale raw se presente (no rete)",
    )
    parser.add_argument(
        "--raw-cache",
        default=None,
        help="path cache CSV raw opzionale (default: data/raw_cache/ sotto il dataset)",
    )
    args = parser.parse_args()

    out_path = Path(args.output)
    cache_path = Path(args.raw_cache) if args.raw_cache else (
        CACHE_DIR / "dati-aggregati-open-cooperazione.csv"
    )
    raw_bytes: bytes | None = None
    if args.skip_download:
        if cache_path.exists() and cache_path.stat().st_size >= MIN_SIZE:
            raw_bytes = cache_path.read_bytes()
            print(f"open_coop_cache_hit path={cache_path} bytes={len(raw_bytes)}")
        else:
            print(f"open_coop_cache_miss path={cache_path}", file=sys.stderr)
            return 1
    elif (
        not args.force
        and cache_path.exists()
        and cache_path.stat().st_size >= MIN_SIZE
        and cache_path.stat().st_mtime >= datetime.now().timestamp() - 36 * 3600
    ):
        raw_bytes = cache_path.read_bytes()
        print(f"open_coop_cache_hit path={cache_path} bytes={len(raw_bytes)}")
    else:
        t0 = time.time()
        raw_bytes = download_csv()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(raw_bytes)
        print(
            f"open_coop_download_ok bytes={len(raw_bytes)} "
            f"elapsed_s={round(time.time() - t0, 1)} cache={cache_path}"
        )

    mapping = load_cf_mapping()
    rows, stats = preprocess(raw_bytes, mapping)
    write_csv(rows, out_path)

    print(
        "open_coop_preprocess_ok "
        f"rows={len(rows)} matched_cf={stats['matched_cf']} "
        f"unmatched={stats['unmatched']} bad_rows={stats['bad_field_count']} "
        f"output={out_path}"
    )
    years = sorted(stats["years"].items(), key=lambda x: x[0])
    print("open_coop_years " + ", ".join(f"{y}:{n}" for y, n in years))
    if stats["matched_cf"] < 50:
        print("open_coop_warn pochi CF matchati — controllare data/cf_mapping.csv", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
