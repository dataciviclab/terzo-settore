# Terzo Settore Intelligence

> Profilo dati di ogni ETS italiano + matching automatico con bandi attivi.

**Prodotto**: per ogni ente del terzo settore (150k iscritti al RUNTS) sapere
chi è, cosa ha fatto (appalti, 5x1000, grant UE, aiuti di stato, PNRR) e
quali bandi potrebbe vincere.

## Cosa fa

```
8 fonti Lab  →  Mart ETS  →  Scheda ETS   (profili 150k enti)
                              Scheda Bando  (top ETS compatibili per bando)
```

| Comando | Cosa ottieni |
|---|---|
| `make scheda-ente CF=02006180364` | Profilo completo di un ETS (ANAC, 5x1000, RNA, UE, PNRR, benchmark territoriale) |
| `make scheda-bando ARGS="5"` | Bando #5: temi, top ETS compatibili, statistiche territoriali |
| `make list-bandi` | Lista dei 70 bandi attivi |
| `make build` | Ricalcola il mart ETS dal toolkit |
| `make bandi` | Aggiorna le fonti bandi (infobandi + info cooperazione) |

## Dati

| Fonte | Cosa dà | ETS matchati |
|---|---|---|
| **RUNTS** | Anagrafe 150k ETS (sezione, comune, provincia) | 150.164 |
| **ANAC** | Appalti pubblici vinti (importi, oggetto, stazione) | 16.417 |
| **5x1000** | Importi erogati 2023-2025 | 71.694 |
| **RNA** | Aiuti di stato (soggetto concedente, procedimento) | 28.893 |
| **PNRR** | Progetti finanziati | 1.397 |
| **FTS/UE** | Grant europei | 338 |
| **MEF** | Immobili pubblici in uso | 3.326 |
| **Subappalti** | ETS come subappaltatori | 119 |

## Stack

- **Toolkit** — pipeline `datasets/` (clean + mart SQL su DuckDB)
- **DuckDB** — query engine per parquet GCS (schede on-demand)
- **match/** — funnel scoring (pertinenza × capacità + bonus 5x1000)
- **bandi/** — scraping fonti bandi (infobandi, info cooperazione)

## Architettura

```
datasets/             Pipeline toolkit (clean + mart SQL)
  ets_unified/          Fatti ETS: 8 fonti Lab → profilo unificato
  runts/                RUNTS: snapshot Runts Nazionale ETS

reports/              Schede on-demand (query DuckDB live)
  scheda_ente.py        Profilo ETS completo
  scheda_bando.py       Profilo bando + ETS compatibili

match/                Matching bandi ↔ ETS
  bando.py              Classificazione bandi
  funnel.py             Scoring: pertinenza × capacità
  pipeline.py           Orchestrazione

bandi/                Acquisizione fonti bandi
  infobandi.py          Fonte: infobandi.csvnet.it
  info_cooperazione.py  Fonte: infocooperazione.it

lib/                  Utility condivise
tsi/                  CLI unica (python3 -m tsi)
```

## Numeri chiave

| KPI | Valore |
|---|---|
| ETS in anagrafe | 150.164 |
| ETS con almeno un fatto pubblico | 90.104 (59%) |
| Appalti ANAC totali | €112.5 mld |
| Bandi attivi tracciati | 70 |
| Fonti dati Lab | 8 |

## Setup

```bash
# Pipeline toolkit (build ETS)
make build

# Aggiorna bandi
make bandi

# Genera schede
make scheda-ente CF=02006180364
make scheda-bando ARGS="5"
make list-bandi
```

---

*Progetto del [DataCivicLab](https://github.com/dataciviclab) — dati aperti, civic tech, impatto sociale.*
