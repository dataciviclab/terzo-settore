#!/usr/bin/env python3
"""Cache locale dei dataset GCS. Scarica una volta, riusa sempre."""

import hashlib, json, os, time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "gcs_cache"
CACHE.mkdir(parents=True, exist_ok=True)
MANIFEST = CACHE / ".manifest.json"

SOURCES = [
    # (slug, year, filename)
    ("anac_aggiudicatari", 2026, "anac_aggiudicatari_2026_clean.parquet"),
    ("anac_aggiudicazioni", 2026, "anac_aggiudicazioni_2026_clean.parquet"),
    ("anac_bandi_gara", 2023, "anac_bandi_gara_2023_clean.parquet"),
    ("anac_bandi_gara", 2024, "anac_bandi_gara_2024_clean.parquet"),
    ("anac_bandi_gara", 2025, "anac_bandi_gara_2025_clean.parquet"),
    ("anac_subappalti", 2026, "anac_subappalti_2026_clean.parquet"),
    ("mef_patrimonio_detenzioni", 2023, "mef_patrimonio_detenzioni_2023_clean.parquet"),
    ("ade_cinque_per_mille", 2023, "ade_cinque_per_mille_2023_clean.parquet"),
    ("ade_cinque_per_mille", 2024, "ade_cinque_per_mille_2024_clean.parquet"),
    ("ade_cinque_per_mille", 2025, "ade_cinque_per_mille_2025_clean.parquet"),
    ("fts_eu_grants", 2020, "fts_eu_grants_2020_clean.parquet"),
    ("fts_eu_grants", 2021, "fts_eu_grants_2021_clean.parquet"),
    ("fts_eu_grants", 2022, "fts_eu_grants_2022_clean.parquet"),
    ("fts_eu_grants", 2023, "fts_eu_grants_2023_clean.parquet"),
    ("fts_eu_grants", 2024, "fts_eu_grants_2024_clean.parquet"),
    ("rna_aiuti_stato", 2025, "rna_aiuti_stato_2025_clean.parquet"),
    ("rna_aiuti_stato", 2026, "rna_aiuti_stato_2026_clean.parquet"),
    ("pnrr_progetti", 2026, "pnrr_progetti_2026_clean.parquet"),
    ("comuni_master", 2026, "comuni_master_2026_clean.parquet"),
]

BASE_URL = "https://storage.googleapis.com/dataciviclab-clean"


def md5_url(url):
    """Prendi etag/md5 da HEAD."""
    try:
        req = urlopen(url)
        etag = req.headers.get("ETag", "").strip('"')
        req.close()
        return etag[:16] if etag else ""
    except:
        return ""


def load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {}


def save_manifest(m):
    MANIFEST.write_text(json.dumps(m, indent=2))


def main():
    manifest = load_manifest()
    downloaded = 0
    cached = 0

    for slug, year, fname in SOURCES:
        url = f"{BASE_URL}/{slug}/{year}/{fname}"
        local = CACHE / fname
        need_download = not local.exists()

        if not need_download and fname in manifest:
            # Check if remote is newer
            remote_md5 = md5_url(url)
            if remote_md5 and remote_md5 != manifest.get(fname, ""):
                need_download = True

        if need_download:
            print(f"  ⬇️  {fname}...", end=" ", flush=True)
            t0 = time.time()
            try:
                req = urlopen(url)
                with open(local, "wb") as f:
                    f.write(req.read())
                dt = time.time() - t0
                size_mb = local.stat().st_size / 1024 / 1024
                manifest[fname] = md5_url(url)
                print(f"{size_mb:.0f}MB in {dt:.0f}s")
                downloaded += 1
            except Exception as e:
                print(f"ERR: {e}")
        else:
            cached += 1

    save_manifest(manifest)
    total = len(SOURCES)
    print(f"\n✅ {cached} in cache, {downloaded} scaricati (tot {total})")


if __name__ == "__main__":
    main()
