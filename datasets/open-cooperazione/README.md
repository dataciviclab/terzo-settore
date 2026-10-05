# open-cooperazione

Dati di trasparenza autodichiarati dalle **OSC italiane attive in cooperazione
allo sviluppo e aiuto umanitario**, dal portale
[Open Cooperazione](https://www.open-cooperazione.it) (progetto
[Info-Cooperazione](https://www.info-cooperazione.it)).

- **Licenza fonte:** CC BY 3.0 IT
- **Perimetro:** ~267 organizzazioni in lista; ~120-160 con dati annuali/anno
- **Anni nel CSV:** 2013–2025 (snapshot multi-anno; `dataset.years: [2026]` = anno di pipeline)
- **Non è tutto il terzo settore:** campione autoselezionato di OSC di cooperazione

## Cosa contiene (per riga = ente × anno)

Anagrafica, forma giuridica, flag ETS/AICS, SDG, bilanci (entrate/uscite, fondi
istituzionali/privati, 5x1000 autodichiarato), risorse umane Italia/estero,
progetti e beneficiari, certificazioni e compliance (231/2001, codice etico).

## Codice fiscale

Il CSV ufficiale **non espone il CF**. Il fetch applica `data/cf_mapping.csv`
(scrape delle schede sito, ~225 CF) con join su nome normalizzato.

## Pipeline

```bash
# solo fetch + preprocessing (raw tidy)
python datasets/open-cooperazione/scripts/fetch_open_cooperazione.py \
  --output /tmp/open_coop_raw.csv

# dataset completo (come gli altri del repo)
make check   # preflight
toolkit run --config datasets/open-cooperazione/dataset.yml
```

Output:

- `out/data/clean/open_cooperazione/2026/open_cooperazione_2026_clean.parquet` — panel multi-anno
- `out/data/mart/open_cooperazione/2026/open_cooperazione_2026_mart.parquet` — stesso panel
- `out/data/mart/open_cooperazione/2026/open_cooperazione_profilo_2026_mart.parquet` — profilo per ente (ultimi dati)

## Preprocessing (perché serve)

Il raw della fonte non è leggibile “as-is” dal toolkit:

| Problema | Gestione |
|---|---|
| encoding latin-1, multi-riga, `;` | parse Python + rewrite UTF-8 |
| header duplicati (Anno x3) | rename per posizione |
| numeri `1.234,56` | normalizzazione a float |
| manca `codice_fiscale` | join `data/cf_mapping.csv` |
| flag SI/NO misti | normalizzazione a `SI`/`NO` |
| HR a 20 colonne separate | aggregate `dipendenti_italia` / `dipendenti_estero` |

`clean.sql` fa solo tipizzazione, flag decode e validazione.

## Join con RUNTS

Su CF: ~92% delle OSC con CF mappa su RUNTS (esplorazione 2026-10-05).
Il compose dedicato (`ets_opencooperazione`) non è ancora definito — si decide
se dedicato o integrazione in `ets_unified`.

## Riferimenti

- Esplorazione: `_local/explorations/open-cooperazione/`
- Bandi già correlati: `bandi/info_cooperazione.py` (sito sorella)
