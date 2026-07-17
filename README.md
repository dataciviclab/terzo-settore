# Terzo Settore Intelligence

**Radar + OSINT per il Terzo Settore italiano.**

Un sistema che incrocia **150.000+ enti del terzo settore (ETS)** con **bandi attivi**, arricchisce i profili con dati pubblici (5x1000, PNRR, Google Places, Open Cooperazione) e produce **segnali d'azione**: bando → ETS candidabile → gap territoriale.

## Cosa fa

```
Bandi (146 operativi/storici) ──┐    ┌─ Deduplicazione + filtro operativo
                                ├──> ├─ Tag extraction + score spiegabile
Anagrafe ETS ──┘    └─ Matching regexp + flag sportivo → Report radar
(150k enti)

55k ETS matchabili • 36 bandi operativi con candidati • 109 esclusi tracciati
```

### Segnali prodotti

| Problema | Segnale |
|----------|---------|
| Castelvolturno RdC 28.5% | Zero ETS sul territorio |
| Baranzate/Corsico RdC >3% | Zero ETS sportivi |
| Fondazione Cariplo pubblica bando | 4 ETS MI candidabili con capacità |
| Bando scade in 7gg | Matching ETS + ranking 5x1000 |

## Architettura

```
data/
  unified_ets.parquet          Hub ETS (150k, 6 MB): capacità, contatti, flags
  runts_iscritti.parquet       Anagrafe RUNTS raw (8 MB)
  oc_organizzazioni.parquet    Open Cooperazione registry (1.592 org, 84 match ETS)
  bandi/                       Cache bandi da tutte le fonti

aggregatori/
  bandi/
    infobandi.py               68 bandi da infobandi.csvnet.it
    info_cooperazione.py       100+ bandi da info-cooperazione.it (ASP.NET)
  enrich_ets.py                OSINT Google Places (sito, tel, rating)
  integra_oc.py                Integrazione Open Cooperazione

sql/
  build_unified_ets.sql        Hub ETS: RUNTS + GCS 5x1000/FTS/RNA/PNRR + OC

radar/
  core.py                      Motore condiviso: bandi, stato, territorio, matching
  scan_completo.py             Scan completo: dedup bandi + match ETS + report
  bandi-in-scadenza.py         Vista latest 60gg dal motore condiviso
  segnale.py                   Report segnale per territorio (comune/provincia)

cruscotto/                     Report markdown generati
```

## Capacità progettuale

Il cuore del matching. Ogni ETS viene classificato su 5 livelli:

| Livello | Criteri | ETS |
|---------|---------|-----|
| **alta** | Grant UE (FTS) | 324 |
| **medio-alta** | Aiuti stato o PNRR | 20.402 |
| **media** | 5x1000 pluriennale o >10k, oppure OC bilancio>100k o ≥3 progetti/dipendenti | 35.490 |
| **base** | 5x1000 presente o Impresa Sociale per statuto o OC bilancio>0 | 19.478 |
| **sconosciuta** | Nessun dato finanziario | 75.110 |

**55.552 ETS matchabili (media+)** — il matching usa solo questi.

### Flag sportivo

- `flag_sport_denom`: **3.214 ETS** identificati per denominazione (vs 261 flag_asd da 5x1000)
- Usato come fallback solo per bandi sportivi, per evitare rumore su bandi non sportivi

## Fonti

| Fonte | Coverage | Dettaglio |
|-------|----------|-----------|
| **RUNTS** | 150.125 ETS | Anagrafe completa (7 sezioni) |
| **5x1000** | 53.831 ETS | Storico donazioni (2023-2025) |
| **FTS grant UE** | 294 ETS | Progetti finanziati |
| **RNA aiuti stato** | 19.562 ETS | Aiuti di stato |
| **PNRR** | 1.086 ETS | Progetti PNRR |
| **Infobandi** | 68 bandi | Fondazioni, PA, EU |
| **Info-cooperazione** | 100+ bandi | Fondazioni bancarie, 8x1000, AICS, EU |
| **Open Cooperazione** | 84 ETS | Bilancio, contatti, progetti (IATI) |
| **Google Places** | 20 ETS | Sito, telefono, rating |

## Setup

```bash
pip install duckdb requests beautifulsoup4 pandas pyarrow

# Genera il radar completo (bandi → match → report)
python radar/scan_completo.py
# Output: cruscotto/radar-completo.md

# Vista bandi operativi in scadenza nei prossimi 60 giorni
python radar/bandi-in-scadenza.py
# Output: cruscotto/radar-latest.md

# Arricchisci ETS con Google Places (opzionale, serve API key)
cp .env.example .env  # Inserisci GOOGLE_MAPS_API_KEY
python aggregatori/enrich_ets.py --candidates MI

# Aggiorna dati Open Cooperazione
python aggregatori/integra_oc.py

# Report segnale per un territorio
python radar/segnale.py --territorio MI --comune Abbiategrasso
```

I dataset 5x1000, FTS grant UE, RNA aiuti stato, PNRR, RdC e indicatori comunali sono letti **direttamente da Google Cloud Storage** (HTTP) — niente cache locale, niente sync. Serve solo DuckDB.

Dipende da **Python 3.10+**, **DuckDB** e librerie standard — niente DB esterni.

## Dataset

- `data/unified_ets.parquet` – **6 MB** – hub ETS completo (150k righe, 33 colonne)
- `data/runts_iscritti.parquet` – **8 MB** – anagrafe raw
- `data/oc_organizzazioni.parquet` – **1 MB** – registry Open Cooperazione
- `data/bandi/` – **~500 KB** – cache bandi

## Roadmap

- [x] Hub ETS unificato (150k enti, capacità progettuale)
- [x] Matching regexp + flag_sport_denom (più preciso del LIKE)
- [x] Capacità rivista: PNRR + pluriennalità + Imprese Sociali + OC
- [x] Deduplicazione bandi tra fonti
- [x] NLP leggero per bandi senza tag
- [x] Aggregatore bandi: infobandi + info-cooperazione
- [x] Open Cooperazione: contatti + capacità
- [x] OSINT Google Places
- [x] Radar completo multi-fonte
- [x] Motore radar condiviso (`radar/core.py`) per report completo e latest
- [ ] Alert automatici (bandi nuovi + scadenze)
- [ ] Pipeline CI per refresh automatico
- [ ] Dashboard interattiva

---

*Progetto del [DataCivicLab](https://github.com/dataciviclab) — dati per l'impatto sociale.*
