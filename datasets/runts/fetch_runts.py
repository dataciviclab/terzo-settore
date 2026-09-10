#!/usr/bin/env python3
"""Download dell'XLSX RUNTS (Registro Unico Nazionale del Terzo Settore).

Fonte istituzionale: Ministero del Lavoro e delle Politiche Sociali.
URL: https://servizi.lavoro.gov.it/runts/it-it/Lista-enti
Pubblicazione: D.Lgs 117/2017 art. 53. Licenza CC BY 4.0 (open data PA).

Il download e' un flusso ASP.NET WebForms in 3 step:
  1. GET sulla pagina per ottenere VIEWSTATE / VIEWSTATEGENERATOR /
     EVENTVALIDATION + cookies di sessione.
  2. Identificazione DINAMICA del bottone btnScaricaDoc associato alla riga
     "Enti iscritti (formato Excel)" della tabella gvEnti (il numero ctlNN
     puo' cambiare tra deploy del Min. Lavoro).
  3. POST form-urlencoded con __EVENTTARGET = nome del bottone.

Uso:
    python fetch_runts.py output.xlsx          # scarica e scrive l'XLSX
    python fetch_runts.py output.xlsx --force  # ignora cache locale del giorno
"""

import argparse
import re
import sys
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

from lab_connectors.http import HttpClient

RUNTS_URL = "https://servizi.lavoro.gov.it/runts/it-it/Lista-enti"
TARGET_ROW_TITLE = "Enti iscritti (formato Excel)"
MIN_SIZE = 1_000_000


def _extract_token(html: str, name: str) -> str:
    m = re.search(rf'name="{name}"\s+id="{name}"\s+value="([^"]+)"', html)
    if not m:
        raise RuntimeError(f"Token ASP.NET '{name}' non trovato nella pagina")
    return m.group(1)


def download_xlsx() -> bytes:
    """Scarica l'XLSX RUNTS via PostBack ASP.NET e ritorna i bytes."""
    t0 = time.time()

    with HttpClient(timeout=30, max_retries=3) as client:
        # Step 1: GET per cookie + tokens
        result = client.get(RUNTS_URL)
        if not result.is_ok or result.response is None:
            raise RuntimeError(f"GET RUNTS fallito: {result.err or result.response.status_code}")
        html = result.response.text

        vs = _extract_token(html, "__VIEWSTATE")
        vsg = _extract_token(html, "__VIEWSTATEGENERATOR")
        ev = _extract_token(html, "__EVENTVALIDATION")

        # Step 2: identifica dinamicamente btnScaricaDoc per la riga target
        table_match = re.search(
            r'<table[^>]*id="dnn_ctr\d+_View_gvEnti"[^>]*>(.+?)</table>',
            html, re.DOTALL,
        )
        if not table_match:
            raise RuntimeError("Tabella gvEnti non trovata nella pagina Lista-enti")
        table = table_match.group(1)

        target_btn = None
        for row in re.findall(r"<tr[^>]*>(.+?)</tr>", table, re.DOTALL):
            if TARGET_ROW_TITLE in row:
                m = re.search(
                    r'name="(dnn\$ctr\d+\$View\$gvEnti\$ctl\d+\$btnScaricaDoc)"', row
                )
                if m:
                    target_btn = m.group(1)
                    break
        if not target_btn:
            raise RuntimeError(
                f"Bottone download per '{TARGET_ROW_TITLE}' non trovato in gvEnti. "
                "Il Min. Lavoro potrebbe aver modificato la struttura della pagina."
            )

        # Step 3: POST con __EVENTTARGET
        data = {
            "__EVENTTARGET": target_btn,
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": vs,
            "__VIEWSTATEGENERATOR": vsg,
            "__EVENTVALIDATION": ev,
            "ScrollTop": "",
            "__dnnVariable": "",
        }
        post_result = client.post(
            RUNTS_URL,
            data=urllib.parse.urlencode(data),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": RUNTS_URL,
            },
            retries=2,
        )
        if not post_result.is_ok or post_result.response is None:
            raise RuntimeError(f"POST RUNTS fallito: {post_result.err or post_result.response.status_code}")

        resp = post_result.response
        ct = resp.headers.get("content-type", "")
        if "octet-stream" not in ct and "spreadsheet" not in ct:
            raise RuntimeError(
                f"Risposta non XLSX: content-type={ct} (size={len(resp.content)} bytes). "
                "Probabilmente la sessione e' scaduta o il bottone e' cambiato."
            )

        elapsed = time.time() - t0
        print(f"runts_download_ok bytes={len(resp.content)} elapsed_s={round(elapsed, 1)}")
        return resp.content


def main() -> int:
    parser = argparse.ArgumentParser(description="Scarica l'XLSX RUNTS dal Min. Lavoro")
    parser.add_argument("output", help="path di output dell'XLSX")
    parser.add_argument("--force", action="store_true", help="ignora cache locale del giorno")
    args = parser.parse_args()

    out_path = Path(args.output)
    today = datetime.now().strftime("%Y%m%d")

    if not args.force and out_path.exists() and out_path.stat().st_size > MIN_SIZE:
        print(f"runts_cache_hit path={out_path}")
        return 0

    content = download_xlsx()
    if len(content) < MIN_SIZE:
        print(f"runts_download_too_small bytes={len(content)}", file=sys.stderr)
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(content)
    print(f"runts_saved path={out_path} bytes={len(content)} snapshot={today}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
