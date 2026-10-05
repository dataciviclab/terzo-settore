# Note tecniche — open-cooperazione

## Raw

- Script: `scripts/fetch_open_cooperazione.py`
- Download ASP.NET: GET `Scarica-Dati.aspx` → POST `__EVENTTARGET=_pulsante_scarica_dati$LK_DOWNLOAD`
- CSV: latin-1, `;`, campi quotati multi-riga, ~110 colonne, ~1.7k righe
- Cache raw: `data/raw_cache/dati-aggregati-open-cooperazione.csv` (non committare)
- CF mapping: `data/cf_mapping.csv` (seed da scrape 2026-10-05, 225 CF)

## Preprocessing

Il fetch non è un semplice download: produce `raw_input.csv` tidy (UTF-8,
snake_case, CF joinato, numeri normalizzati). Motivo: il toolkit legge il raw
primario con parametri CSV semplici; il raw della fonte ha header duplicati e
parsing multi-riga non esprimibile in `clean.read`.

## Clean / Mart

- `clean.sql`: CAST + `decode_flag` + `normalize_string`; droppa social/PDF free-text
  (info ancora nel raw se servono — lens transizione)
- `mart.sql`: panel clean
- `mart_profilo.sql`: ultimi dati per ente (PK logica: CF o `NOME:`+nome)

## Anni

`dataset.years: [2026]` = anno di pipeline (snapshot). Il clean contiene il
panel 2013-2025 dentro lo stesso parquet — stesso pattern RUNTS.

## Join RUNTS (esplorazione)

- CF scrape: 227/267 org; matchati RUNTS: 207 (92%)
- 5x1000 ADE: 203/207 presenti; ANAC 57; RNA 146; coesione 4; FTS 5; PNRR 2
- Caveat: autodichiarato; anomalie bilancio (es. valori fuori scala) da validare in dashboard

## Qualità dati — outlier bilancio

**Caso noto: Comunità di S. Egidio ACAP APS** (CF 80191770587).

| Anno | Entrate |
|---|---|
| 2019–2024 | 20–32 mln € (serie stabile) |
| 2025 | **3.398.070.400 €** |

Verificato sulla pagina fonte open-cooperazione.it: il valore è identico —
non è un bug del nostro parser. Probabile errore di inserimento (cifre/zeri);
un valore coerente con la serie sarebbe ~34 mln.

Gestione in pipeline:
- `clean.sql` → colonna `is_bilancio_outlier` (TRUE se entrate > 1 mld €)
- il dato **non viene droppato**: resta nel clean per tracciabilità
- i totali analitici/dashboard devono filtrare il flag
- soglia 1 mld: plausibile per ONLUS/ONG di cooperazione (Save the Children
  ~180 mln resta incluso)

## Prossimo passo (aperto)

Compose: dedicato `compose/ets_opencooperazione` vs arricchimento `ets_unified`.
Valutare dopo primo clean riuscito. Decisione corrente: **fuori compose** —
campione troppo piccolo (~250 org) per giustificare un compose dedicato;
usato come layer di arricchimento + pagina dashboard.
