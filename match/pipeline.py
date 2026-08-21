"""Orchestrazione scan: carica bandi, matcha, produce risultati."""

import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]

from lib.config import BANDI_FILES
from lib.html_utils import arricchisci
from lib.format import parse_date_flex
from match.bando import classify_bando, extract_tags_from_text, normalise_bando
from match.funnel import match_bando_funnel


def deduplicate_bandi(bandi):
    unique = []
    seen_urls = set()
    seen_keys = set()

    for b in sorted(bandi, key=lambda x: len(x.get("tag", x.get("tags", [])) or []), reverse=True):
        url_b = (b.get("url", "") or "").strip()
        if url_b and url_b in seen_urls:
            continue

        ente = (b.get("ente_erogatore", b.get("donatore", "")) or "").strip().lower()
        scadenza_raw = (b.get("scadenza", "") or "").strip().lower()
        import re
        ente_norm = re.sub(r'\b(for|the|di|del|della|per|e|ed|a|children|foundation)\b', '', ente).strip()
        ente_norm = re.sub(r'\s+', ' ', ente_norm).strip()
        m_scad = re.match(r'(\d{1,2})\s+([a-z]+)\s+(\d{4})', scadenza_raw)
        scadenza = f"{int(m_scad.group(1)):02d}{m_scad.group(2)}{m_scad.group(3)}" if m_scad else scadenza_raw[:20]

        if not ente_norm or ente_norm in ('?', ''):
            titolo = (b.get("titolo", b.get("title", "")) or "").strip().lower()
            titolo_norm = re.sub(r'[^a-z0-9 ]', '', titolo)
            titolo_norm = re.sub(r'\s+', ' ', titolo_norm).strip()
            key = titolo_norm[:40]
        else:
            key = f"{ente_norm[:40]}|{scadenza[:20]}"

        if key in seen_keys:
            continue

        if not ente_norm or ente_norm in ('?', ''):
            titolo_b = (b.get("titolo", b.get("title", "")) or "").strip().lower()
            for existing_key in seen_keys:
                if '|' not in existing_key:
                    if len(titolo_b) > 20 and len(existing_key) > 20:
                        if titolo_b[:30] in existing_key or existing_key[:30] in titolo_b:
                            key = existing_key
                            break

        seen_urls.add(url_b)
        seen_keys.add(key)
        unique.append(b)
    return unique


def load_bandi(files=None):
    bandi = []
    for fpath in files or BANDI_FILES:
        try:
            with open(fpath, encoding="utf-8") as f:
                raw = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        fonte = "infobandi" if "infobandi" in fpath.name else "info_cooperazione"
        if isinstance(raw, list):
            for b in raw:
                b["_fonte"] = fonte
            bandi.extend(raw)
        elif isinstance(raw, dict) and "bandi" in raw:
            for b in raw["bandi"]:
                b["_fonte"] = fonte
            bandi.extend(raw["bandi"])
    return deduplicate_bandi(bandi)


def process_bando(con, b, tags, territorio, match_limit=20, testo=None):
    """Match un bando: conta gli idonei (senza cap) e seleziona il top-N.

    Ritorna dict con:
      - candidati: top-N ordinati per score
      - n_idonei: totale ETS idonei (senza cap di match_limit)
      - codici_fiscali: set dei top-N
    """
    df = match_bando_funnel(con, tags, limit=match_limit, territorio=territorio, testo=testo)
    if df.empty:
        return None

    # Conteggio idonei reale (senza cap) — separato dalla selezione top-N
    n_idonei = len(df)
    try:
        df_all = match_bando_funnel(con, tags, limit=10_000_000, territorio=territorio, testo=testo)
        n_idonei = len(df_all)
    except Exception:
        pass  # se il conteggio senza cap fallisce, resta il valore del top-N

    return {
        "candidati": df.to_dict("records"),
        "n_idonei": n_idonei,
        "codici_fiscali": set(df["codice_fiscale"].tolist()) if "codice_fiscale" in df.columns else set(),
    }


def elabora_bando(b, con, match_limit=20):
    titolo, url, scadenza_str, ente, tags, territorio, fonte = normalise_bando(b)
    scadenza, gg_rimasti = parse_date_flex(scadenza_str)
    status, status_motivo = classify_bando(b, scadenza, gg_rimasti)

    if status not in ("attivo", "sportello"):
        return {"tipo": "skipped", "titolo": titolo, "url": url, "ente": ente,
                "scadenza": scadenza_str, "status": status, "motivo": status_motivo}

    if fonte == "info_cooperazione" and not tags:
        testo = b.get("testo_nlp", "") or b.get("descrizione", "") or ""
        if len(testo) < 500 and url:
            extra = arricchisci(url)
            testo_lungo = extra.get("testo_nlp", "")
            if len(testo_lungo) > len(testo):
                nlp_tags = extract_tags_from_text(testo_lungo)
                if nlp_tags:
                    tags = nlp_tags

    if not b.get("budget") and url:
        extra = arricchisci(url)
        if extra.get("budget"):
            b["budget"] = extra["budget"]
        if extra.get("territorio"):
            if not territorio or territorio == ["Nazionale/da verificare"]:
                territorio = extra["territorio"]

    # Il funnel (match_bando_funnel) deriva la pertinenza dai tag
    # normalizzati + testo, non dal pattern grezzo.
    testo_bando = " ".join(str(b.get(k, "") or "") for k in
                           ("titolo", "descrizione", "obiettivi", "ammissibili", "testo_nlp"))

    result = process_bando(con, b, tags, territorio, match_limit, testo=testo_bando)
    if result is None:
        return {"tipo": "sin_match", "titolo": titolo, "url": url, "ente": ente,
                "scadenza": scadenza_str, "gg": gg_rimasti, "tags": tags,
                "territorio": territorio, "status": status, "motivo": "nessun ETS matcha"}

    return {
        "tipo": "match",
        "titolo": titolo, "url": url, "ente": ente,
        "budget": b.get("budget"), "scadenza": scadenza_str,
        "gg": gg_rimasti, "tags": tags, "territorio": territorio,
        "status": status,
        "candidati": result["candidati"],
        "n_idonei": result.get("n_idonei", len(result["candidati"])),
        "codici_fiscali": result["codici_fiscali"],
    }


def run_scan(con=None, bandi=None, match_limit=20, include_statuses=None):
    con = con or duckdb.connect()
    bandi = bandi or load_bandi()

    resultados = []
    sin_match = []
    skipped = []
    stats_ets = set()

    for b in bandi:
        esito = elabora_bando(b, con, match_limit)
        t = esito["tipo"]
        if t == "skipped":
            skipped.append({k: esito[k] for k in ("titolo", "url", "ente", "scadenza", "status", "motivo")})
        elif t == "sin_match":
            sin_match.append(tuple(esito[k] for k in ("titolo", "url", "ente", "scadenza", "gg", "tags", "territorio", "status", "motivo")))
        else:
            stats_ets.update(esito["codici_fiscali"])
            resultados.append({k: esito[k] for k in ("titolo", "url", "ente", "budget", "scadenza", "gg", "tags", "territorio", "status", "candidati", "n_idonei")})

    return {
        "bandi": bandi,
        "resultados": resultados,
        "sin_match": sin_match,
        "skipped": skipped,
        "stats_ets": stats_ets,
    }
