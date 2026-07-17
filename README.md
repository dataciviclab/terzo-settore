# Terzo Settore Intelligence

**Radar + contatti per il Terzo Settore italiano.**

Un sistema che incrocia **150.000+ enti del terzo settore (ETS)** con **bandi attivi**,
arricchisce i profili con dati pubblici (5x1000, PNRR, Open Cooperazione, Google Places)
e produce **segnali d'azione**: bando → ETS candidabile → contatto telefonico.

## Stato attuale

```
Bandi (268 lordi, 48 attivi) ──┐    ┌─ Dedup + tag (NLP + fonti)
                                ├──> ├─ Match per sezione RUNTS + denominazione
Anagrafe ETS (150k) ──┘    └─ Score: tema 60% + capacità 20% + bonus sezione 20%

45 bandi matchati • 164 ETS unici coinvolti • 1 gap operativo
```

### Vantaggi rispetto al matching su sola denominazione

| Problema pre-fix | Come è stato risolto |
|---|---|
| Stessi 10 ETS dominavano tutti i bandi | **Sezione RUNTS come gate**: bonus +25 punti per ETS nella sezione pertinente al bando |
| Score 74% baseline, 26% tema | **Score ribilanciato**: tema 60% + sezione 10% + capacità 20% + bonus 10% |
| Bandi Mezzogiorno → candidati Milano | **Filtro geografico**: mappa 20 regioni → province, filtrato in SQL |
| DAPHNE taggato "sport" (falso positivo) | **Strategia mista tag**: NLP + nativi validati (keyword nel testo, non nell'HTML) |
| Report ricalcolato 3 volte | **Scan → JSON cache**: latest, segnale e contatta leggono dal JSON |

## Architettura

```
data/
  unified_ets.parquet          Hub ETS (150k, 6 MB): capacità, contatti, flags
  runts_iscritti.parquet       Anagrafe RUNTS raw (8 MB)
  oc_organizzazioni.parquet    Open Cooperazione registry (1.592 org)
  bandi/                       Cache bandi (268 da 2 fonti)

aggregatori/bandi/
  infobandi.py                 68 bandi da infobandi.csvnet.it (API WordPress)
  info_cooperazione.py         200 bandi da info-cooperazione.it (scraping)

sql/
  build_unified_ets.sql        Hub ETS: RUNTS + 5x1000/FTS/RNA/PNRR + OC

radar/
  core.py                      Motore: matching, score, sezioni, filtro geo
  scan_completo.py             Scan completo → JSON + Markdown
  bandi-in-scadenza.py         Vista 60gg (legge da JSON scan)
  segnale.py                   Report per territorio (legge da JSON scan)
  contatta.py                  Esporta CSV candidati da contattare

cruscotto/                     Report generati (Markdown + JSON)
tools/                         Archvio (integrazioni one-shot)
```

## Flusso

```
make scan  ──→  cruscotto/radar-completo.json   (scan unico)
                     │
                     ├── make latest             (bandi in scadenza)
                     ├── make segnale T=MI       (report territorio)
                     └── make contatta B="BPER"  (csv da importare)
```

## Capacità progettuale

Ogni ETS viene classificato su 5 livelli. Il matching usa solo **media+** (55k ETS):

| Livello | Criteri | ETS |
|---------|---------|-----|
| **alta** | Grant UE (FTS) | 294 |
| **medio-alta** | Aiuti stato o PNRR | 20.111 |
| **media** | 5x1000 pluriennale o >10k, OC bilancio>100k o ≥3 progetti/dipendenti | 35.147 |
| **base** | 5x1000 presente, Impresa Sociale, OC bilancio>0 | 19.463 |
| **sconosciuta** | Nessun dato finanziario | 75.110 |

## Fonti

| Fonte | Coverage | Dettaglio |
|-------|----------|-----------|
| **RUNTS** | 150.125 ETS | Anagrafe completa (7 sezioni) |
| **5x1000** | 53.831 ETS | Storico donazioni (2023-2025) |
| **FTS grant UE** | 294 ETS | Progetti finanziati |
| **RNA aiuti stato** | 19.562 ETS | Aiuti di stato |
| **PNRR** | 1.086 ETS | Progetti PNRR |
| **Infobandi** | 68 bandi | Fondazioni, PA, EU |
| **Info-cooperazione** | 200 bandi | Cooperaz., 8x1000, AICS, EU |
| **Open Cooperazione** | 1.592 org | Bilancio, contatti, progetti |
| **Google Places** | opzionale | Sito, telefono, rating |

## Setup

```bash
pip install duckdb requests beautifulsoup4 pandas pyarrow python-dotenv
```

### Uso quotidiano

```bash
# 1. Scan completo (bandi → match → report JSON)
make scan

# 2. Bandi in scadenza nei prossimi 60gg
make latest
# Output: cruscotto/radar-latest.md

# 3. Candidati da contattare per un bando specifico
make contatta B="sport inclusivo" TOP=10
# Output: contatta-sport-inclusivo-20260717.csv

# 4. Con Google Places (arricchisce telefono/sito mancanti)
cp .env.example .env  # Inserisci GOOGLE_MAPS_API_KEY
make contatta B="BPER" ENRICH=1
# 3/3 contattabili con telefono

# 5. Cerca bandi per uno specifico ETS
python3 radar/contatta.py --cf 90081250632

# 6. Report segnale per comune/provincia
make segnale T=MI C=Abbiategrasso
# Output: cruscotto/segnale-abbiategrasso.md
```

### Test

```bash
make test          # 40+ test: matching, sezioni, geografia, NLP, integrità scan
```

I dataset 5x1000, FTS grant UE, RNA aiuti stato, PNRR, RdC e indicatori comunali
sono letti **direttamente da Google Cloud Storage** — niente cache locale.

Dipende da **Python 3.10+**, **DuckDB** e librerie standard.

## Dataset

- `data/unified_ets.parquet` – **6 MB** – hub ETS completo (150k righe, 33 colonne)
- `data/runts_iscritti.parquet` – **8 MB** – anagrafe RUNTS
- `data/oc_organizzazioni.parquet` – **1 MB** – registry Open Cooperazione
- `data/bandi/` – **~500 KB** – cache bandi (268 bandi)
- `data/enrich/` – cache Google Places (generato da `--enrich`)

## Roadmap

- [x] Hub ETS unificato (150k enti, capacità progettuale)
- [x] Matching per sezione RUNTS + denominazione (score tematico 60%)
- [x] Filtro geografico per regione/provincia
- [x] Tag puliti: strategia mista NLP + nativi validati
- [x] Scan singolo → cache JSON → tutti i report
- [x] Esportazione CSV candidati da contattare (`contatta.py`)
- [x] Arricchimento Google Places opzionale
- [x] 40+ test automatizzati
- [ ] Alert automatici (bandi nuovi + scadenze)
- [ ] Pipeline CI per refresh settimanale
- [ ] Dashboard interattiva

---

*Progetto del [DataCivicLab](https://github.com/dataciviclab) — dati per l'impatto sociale.*
