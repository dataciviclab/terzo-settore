# Terzo Settore Intelligence — DataCivicLab

**Per ogni ETS italiano, chi è, cosa ha fatto e quali bandi potrebbe vincere.**

Sistema di intelligence sul terzo settore italiano: raccoglie 8 fonti pubbliche
(RUNTS, ANAC, 5x1000, RNA, PNRR, FTS/UE, MEF, OpenCoesione) per costruire un
profilo unificato di ogni ente iscritto al Registro Unico Nazionale del Terzo
Settore, e lo collega automaticamente ai bandi attivi.

- **Stato:** beta
- **Copertura:** 2026, Italia (150k ETS)
- **Unità di analisi:** Ente (codice_fiscale)

## La domanda civica

**Quali risorse riceve il terzo settore italiano, come si distribuiscono tra
territori e sezioni, e quali bandi potrebbero essere vinti dagli enti con
maggiore capacita progettuale?**

Esempi:
- Il mio ente ha ricevuto risorse pubbliche? Da quali fonti?
- Quanti ETS nella mia provincia hanno partecipato ad appalti ANAC?
- Quali bandi sono compatibili con un ente di volontariato a Bologna?

## Dataset

| Slug | Cosa contiene | Anni | Stato |
|---|---|---|---|
| `runts` | Anagrafe 150k ETS iscritti al RUNTS | 2026 | published |
| `ade_cinque_per_mille` | Elenchi beneficiari 5x1000 ADE (download CSV) | 2022-2025 | beta |
| `istat_non_profit_2023` | Censimento ISTAT non profit (regioni, province, settori) | 2023 | beta |
| `ets_5xmille` | Compose: RUNTS + 5x1000 (ADE) | 2026 | beta |
| `ets_anac` | Compose: RUNTS + ANAC (aggiudicazioni, partecipazioni, subappalti) | 2026 | beta |
| `ets_pnrr` | Compose: RUNTS + PNRR | 2026 | beta |
| `ets_rna` | Compose: RUNTS + RNA aiuti di stato | 2026 | beta |
| `ets_fts` | Compose: RUNTS + FTS grant europei | 2026 | beta |
| `ets_mef` | Compose: RUNTS + MEF patrimonio immobiliare | 2026 | beta |
| `ets_opencoesione` | Compose: RUNTS + OpenCoesione fondi coesione | 2026 | beta |
| `ets_unified` | Fatti ETS (long) + profilo unificato + aggregato comunale | 2026 | beta |

## Dashboard Streamlit

```bash
pip install -e ".[dashboard]"
streamlit run dashboard/app.py
```

Pagine:
- **Panoramica** — KPI: ETS totali, per fonte, capacita progettuale
- **Anagrafe RUNTS** — esplorazione per sezione, territorio
- **5x1000** — trend, flag tematici, top ETS
- **Trasparenza** — RNA + ANAC
- **Programmi** — PNRR + grant UE
- **Scheda ETS** — profilo completo con bandi compatibili
- **Bandi Attivi** — lista bandi con filtri
- **Matching** — trova ETS candidati per un bando
- **Territorio** — vista per regione/provincia
- **Censimento** — ISTAT non profit 2023

## Architettura

```
datasets/
  runts/                     Anagrafe 150k ETS (fetch XLSX da Ministero)
  ade-cinque-per-mille/      Elenchi 5x1000 ADE (download CSV, 2022-2025)
  istat_non_profit_2023/     Censimento ISTAT (CSV locale)

compose/
  ets_5xmille/               RUNTS + ADE 5x1000 → clean + mart
  ets_anac/                  RUNTS + ANAC → clean + 3 mart (agg/part/sub)
  ets_pnrr/                  RUNTS + PNRR → clean + mart
  ets_rna/                   RUNTS + RNA → clean + mart
  ets_fts/                   RUNTS + FTS → clean + mart
  ets_mef/                   RUNTS + MEF → clean + mart
  ets_opencoesione/          RUNTS + OpenCoesione → clean + mart
  ets_unified/               Tutti i clean locali → UNION ALL → mart pivot

dashboard/                   Streamlit (10 pagine)
bandi/                       Acquisizione bandi (infobandi, info-cooperazione)
lib/                         Utility (parsing scadenze bandi)
```

### Pipeline

```bash
make run
  1. toolkit run datasets/runts/                → runts_clean.parquet
  2. toolkit run datasets/ade-cinque-per-mille/ → 5x1000 clean + mart (2022-2025)
  3. toolkit run datasets/istat_non_profit_2023/ → istat_clean + mart
  4. toolkit run compose/ets_{fonte}/           → clean + mart per fonte (x7)
  5. toolkit run compose/ets_unified/           → fatti long + profilo + comuni
```

I compose legge le fonti da GCS o dai dataset locali, le joina con RUNTS e produce clean + mart.
`ets_unified` legge i clean locali dei compose e li unifica.

## Fonti

| Fonte | Cosa da | ETS matchati |
|---|---|---|
| **RUNTS** | Anagrafe 150k ETS (sezione, comune, provincia) | 150.164 |
| **ANAC** | Appalti pubblici vinti (importi, oggetto, stazione) | 16.417 |
| **5x1000** | Importi erogati 2022-2025 | 95.977 |
| **RNA** | Aiuti di stato (soggetto concedente, procedimento) | 28.893 |
| **PNRR** | Progetti finanziati | 1.397 |
| **FTS/UE** | Grant europei | 338 |
| **MEF** | Immobili pubblici in uso | 3.326 |
| **OpenCoesione** | Progetti fondi coesione | ~100k |

## Setup

```bash
# Pipeline completa
make run

# Validazione config
make check

# Aggiorna bandi
make bandi

# Registry
make registry
```

## Confine con il toolkit

Il motore della pipeline vive nel repository `toolkit`. Questa repo non replica
la logica di esecuzione: definisce input, regole e output attesi per ogni dataset.

- bug o feature di CLI, runner, validazioni runtime → repo `toolkit`
- bug o modifiche a fonti, mapping, SQL, mart, docs → questa repo

## Partecipa

- **Discussions** → domande civiche, interpretazioni, proposte di metriche
- **Issues** → bug, problemi tecnici, miglioramenti della pipeline

## Riferimenti

- [DataCivicLab](https://dataciviclab.org/)
- [Toolkit](https://github.com/dataciviclab/toolkit)
- [.github](https://github.com/dataciviclab/.github)

---

*Progetto del [DataCivicLab](https://github.com/dataciviclab) — dati aperti, civic tech, impatto sociale.*
