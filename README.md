# Terzo Settore Intelligence

**Profilo di capacità di ogni ETS italiano + quali contattare per un bando.**

Il repo produce il **profilo dati di ogni ente del terzo settore** (intelligence,
layer 1) e lo usa per **indicare quali ETS contattare per un bando** (operativo,
layer 2). Il monitoraggio territoriale (radar, gap) è un sotto-prodotto del profilo.

## Scopo in una frase

> Da un bando a una lista di ETS da contattare — con il profilo di capacità
> (5x1000, appalti, grant UE, PNRR, aiuti di Stato, subappalti, immobili) come
> base dati condivisa.

## Come funziona

```
LAYER 1 — INTELLIGENCE (il prodotto, serializzato)
  make build
  → data/unified_ets.parquet   (profilo 150k ETS: capacità, fonti, geografia)
  → data/comuni_ets.parquet    (aggregato per comune)
  Riusabile da: match, analisi Lab. È IL deliverable.

LAYER 2 — OPERATIVO (il servizio, on-demand)
  make bandi                   (aggiorna le 3 fonti)
  make contatta B="RIZA"       (CSV contatti per un bando → cruscotto/output/)
  make latest                  (radar bandi in scadenza)
  Consuma il LAYER 1, non lo ricostruisce.

LAYER 3 — SPERIMENTALE (isolato su branch feat/experiments)
  dashboard, network graph, partnership
  Non tocca il LAYER 1 e 2.
```

## Esempi d'uso

| Scenario | Comando | Cosa ottieni |
|---|---|---|
| "Bando RIZA da €1M, chi contatto?" | `make contatta B="RIZA" ENRICH=1` | 10 ETS con telefono |
| "Bandi urgenti questa settimana" | `make latest` | Bandi in scadenza + gap territoriali |
| "Comune X ha pochi ETS?" | `make segnale T=MI C=Abbiategrasso` | Landscape ETS + contesto sociale |
| "Pacchetto per il CSV" | `make pacchetto T=BO` | Deliverable territorio → `data/reporting/territorio_BO.json` |
| "Profilo Nazareno" | `make report CF=02006180364` | Benchmark, ANAC, bandi matchati |
| "Contratti recenti di Nazareno" | `make scheda CF=02006180364 OPZIONI=--anac` | Oggetto, importo, stazione appaltante |

## Pipeline

```bash
make all              # build + comuni-ets + scan completo
make bandi            # aggiorna le 3 fonti bandi
make contatta B="RIZA" TOP=10 ENRICH=1   # CSV con telefono → cruscotto/output/
make sync-sources     # mostra da dove arriva ogni parquet (lab/cache/gcs)
```

## Connessione col mondo CSV (T1/T2)

Il ponte tra il Lab e la rete CSVnet è il **pacchetto territorio**: un file
JSON auto-contenuto per provincia (`make pacchetto T=BO` → `data/reporting/territorio_BO.json`)
con aggregati ETS, contesto sociale, bandi con match locale e gap territoriali.

Chiave di giunzione bidirezionale:
- **bando**: `id` Infobandi (o hash stabile dell'url per le altre fonti)
- **ETS**: `codice_fiscale`

Il CSV può restituire il feedback ("ETS X si è candidato al bando Y") che il
Lab riconcilia per migliorare il matching. Config dei territori target in
`match/reports/pacchetto.py` (`TERRITORI_TARGET`). Limite privacy: nel
pacchetto solo aggregati + matching, mai liste contatti.

## Architettura

```
datasets/                         ← Pipeline toolkit (clean + mart SQL)
  ets_unified/                      Fatti ETS: 8 fonti Lab → profilo unificato
  runts/                            RUNTS: snapshot Runts Nazionale ETS

reports/                          ← Schede ETS on-demand
  scheda_ente.py                    Profilo completo: ANAC/5x1000/RNA/UE/PNRR + benchmark

match/                            ← Matching bandi ↔ ETS
  bando.py                          Classificazione bandi (temi, budget, territorio)
  funnel.py                         Scoring: pertinenza × capacità + bonus 5x1000
  pipeline.py                       Orchestrazione: load_bandi → run_scan

bandi/                            ← Acquisizione fonti bandi
  infobandi.py                      Fonte: infobandi.csvnet.it (CSVNet)
  info_cooperazione.py              Fonte: infocooperazione.it

lib/                              ← Utility condivise
  config.py                         Costanti, path, soglie
  format.py                         Formattazione output
  temi.py                           Estrazione e match tematico
  html_utils.py                     Parsing HTML bandi

tsi/                              ← CLI unica (python3 -m tsi)
  cli.py                            Dispatch: scheda-ente
```

## Regole di funzionamento

1. **Pipeline toolkit**: `datasets/ets_unified/` produce il mart ETS (clean + mart SQL).
   `reports/scheda_ente.py` genera le schede on-demand.
2. **Matching bandi**: `match/` classifica e matcha bandi contro il profilo ETS.
   Fonti in `bandi/`, output in `data/bandi/`.
3. **Output generati** (JSON bandi, schede markdown) non dovrebbero essere versionati
   se rigenerabili — vedi `.gitignore`.
4. **Nomi che dicono la verità**: niente `tsi/` o `radar/` inesistenti; SQL generato
   in `data/build/`, non in `/tmp`.
5. **Sperimentazione isolata**: dashboard/network/partnership solo su `feat/experiments`.

## Driver-first: perché non si scarica tutto

Il repo consuma i clean parquet del Lab **in-place**, senza copiarli:
`resolve_sources.py` cerca ogni file prima nel layer Lab locale, poi nella cache,
infine su GCS. La build di `fatti_ets` usa il RUNTS (150k CF) come driver e filtra
ogni fonte per codice fiscale → produce **485K righe invece di 9.1M** (−95%).
Il download da GCS avviene solo per i file che il Lab non ha ancora prodotto
localmente, e una sola volta.

## Fonti dati

| Dataset | Cosa dà |
|---|---|
| **fatti_ets** (485K righe) | Long format: fonte, cf, anno, importo, oggetto_gara, stazione_appaltante, appalto_riservato, flag_pnrr |
| **unified_ets** (150K ETS) | 32 colonne: capacità, geografia, appalti riservati, PNRR, subappalti, patrimonio immobiliare |
| RUNTS | Anagrafe ETS (sezione, comune, provincia) |
| ANAC aggiudicazioni + bandi_gara | Appalti pubblici: importi, oggetto, riservati (L.381/91, D.Lgs 117/2017), PNRR |
| ANAC subappalti | ETS come subappaltatori (119 ETS, 363 subappalti) |
| MEF patrimonio detenzioni | Immobili pubblici in uso a ETS (3.301 ETS, 6.163 immobili) |
| 5x1000, FTS, RNA, PNRR | Capacità fundraising, europea, aiuti, Next Gen EU |

## Numeri chiave

*Basati su ETS effettivamente iscritti al RUNTS (150.164) — join per codice fiscale.*

| KPI | Valore |
|---|---|
| Bandi attivi tracciati | 131 (3 fonti) |
| ETS in anagrafe | 150.164 |
| ETS con 5x1000 (2023-2025) | 57.202 |
| ETS con appalti ANAC | 16.350 (€126Mld) |
| ETS con appalti riservati | 332 |
| ETS con grant UE | 302 |
| ETS con PNRR | 1.363 |
| ETS con subappalti | 119 |
| ETS con immobili pubblici | 3.301 |

> **Nota**: il 93% dei soggetti PNRR (20.703) e il 94% dei beneficiari FTS UE non
> sono ETS iscritti al RUNTS — sono imprese, università, PA. Il driver-first li
> esclude correttamente: i numeri sopra contano solo enti del terzo settore.

---

*Progetto del [DataCivicLab](https://github.com/dataciviclab) — dati aperti, civic tech, impatto sociale.*
