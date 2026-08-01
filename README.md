# Terzo Settore Intelligence

**Da un bando a una lista di numeri di telefono in due comandi.**

Matcha 150.000 ETS italiani con bandi pubblici e privati. Arricchisce con
appalti ANAC, donazioni 5x1000, grant UE, PNRR, aiuti di Stato, subappalti,
immobili pubblici. Esporta CSV con contatti telefonici pronti per chiamata.

## Esempi d'uso

| Scenario | Comando | Cosa ottieni |
|---|---|---|
| "Bando RIZA da €1M, chi contatto?" | `make contatta B="RIZA" ENRICH=1` | 10 ETS con telefono |
| "Bandi urgenti questa settimana" | `make latest` | Bandi in scadenza + gap territoriali |
| "Comune X ha pochi ETS?" | `make segnale T=MI C=Abbiategrasso` | Landscape ETS + contesto sociale |
| "Profilo Nazareno" | `make report CF=02006180364` | Benchmark, ANAC, bandi matchati |
| "Contratti recenti di Nazareno" | `make scheda CF=02006180364 OPZIONI=--anac` | Oggetto, importo, stazione appaltante |
| "Tutto pronto per lunedì" | `make lunedi` | Scan + CSV RIZA/UEFA/BPER |

## Pipeline

```bash
make build       # fatti_ets (8.8M righe, 7 fonti) → PIVOT → unified_ets (150K ETS, 33 colonne)
make all         # build + comuni-ets + scan completo
make latest      # bandi ≤60gg + TOP opportunità + gap territoriali
make contatta B="RIZA" TOP=10 ENRICH=1   # CSV con telefono
```

## Architettura

```
ets/                              ← Hub dati ETS
  resolve_sources.py              Risoluzione sorgenti: layer Lab locale → cache → GCS
  build_fatti_ets_driver.sql      Template driver-first: RUNTS 150k CF → join filtrato
                                  con 7 fonti (5x1000, grant_ue, aiuto_stato, pnrr,
                                  anac, subappalto, patrimonio) — materializza SOLO
                                  gli ETS (485K righe vs 9.1M prima)
  build_unified_ets.sql           PIVOT da fatti_ets + geografia (comuni_master) + temi ANAC
  enrich_temi.py                  NLP su oggetti ANAC → temi per ETS
  comuni.py                       Metriche aggregate per comune

match/                            ← Matching bandi ↔ ETS
  matcher.py                      Motore: match_bando (sezione + keyword + territorio)
  pipeline.py                     Orchestrazione: load_bandi → run_scan
  reports/
    scan_completo.py              Scan → radar-completo.json/md. Flag: --latest, --territorio
    contatta.py                   CSV contatti per bando. Flag: --per-ets, --enrich
    scheda.py                     Profilo ETS: benchmark, ANAC (oggetti gara), bandi matchati

bandi/                            ← Acquisizione (3 fonti)
  infobandi.py, info_cooperazione.py, indicebandi.py

lib/                              ← Utility condivise
```

> **Sperimentazioni** (dashboard Streamlit, network graph, partnership) vivono nel
> branch `feat/experiments` — non su main, per tenere il core stabile e senza
> dipendenze pesanti (networkx, pyvis, matplotlib).

### Driver-first: perché non si scarica tutto

Il repo consuma i clean parquet del Lab (layer `dataset-incubator/out/data/clean/`)
**in-place**, senza copiarli: `resolve_sources.py` cerca ogni file prima nel layer
Lab locale, poi nella cache TSI, infine su GCS. La build di `fatti_ets` usa il
RUNTS (150k CF) come driver e filtra ogni fonte per codice fiscale → produce
**485K righe invece di 9.1M** (−95%, 12MB invece di 320MB). Il download da GCS
avviene solo per i file che il Lab non ha ancora prodotto localmente, e una sola
volta (la cache li conserva validati).

## Fonti dati

| Dataset | Cosa dà |
|---|---|
| **fatti_ets** (8.8M righe) | Long format: fonte, cf, anno, importo, oggetto_gara, stazione_appaltante, appalto_riservato, flag_pnrr |
| **unified_ets** (150K ETS) | 33 colonne: capacità, geografia (98% con istat/regione), appalti riservati, PNRR, subappalti, patrimonio immobiliare |
| RUNTS | Anagrafe ETS (sezione, comune, provincia) |
| ANAC aggiudicazioni + bandi_gara | Appalti pubblici: importi, oggetto, riservati (L.381/91, D.Lgs 117/2017), PNRR |
| ANAC subappalti | ETS come subappaltatori (119 ETS, 363 subappalti) |
| MEF patrimonio detenzioni | Immobili pubblici in uso a ETS (3.301 ETS, 6.163 immobili) |
| 5x1000, FTS, RNA, PNRR | Capacità fundraising, europea, aiuti, Next Gen EU |

## Numeri chiave

*Basati su ETS effettivamente iscritti al RUNTS (150.164) — join per codice fiscale.
Prima della refactor driver-first, le metriche PNRR/UE contavano anche soggetti
non ETS (imprese, PA): vedi sezione "Architettura".*

| KPI | Valore |
|---|---|
| Bandi attivi tracciati | 131 (3 fonti) |
| ETS in anagrafe | 150.164 |
| ETS con 5x1000 (2023-2025) | 57.202 |
| ETS con appalti ANAC | 16.350 (€140Mld) |
| ETS con appalti riservati | 332 |
| ETS con grant UE | 302 |
| ETS con PNRR | 1.363 |
| ETS con subappalti | 119 |
| ETS con immobili pubblici | 3.301 |
| ETS con tutte le fonti (5/7) | 12 |

> **Nota sulla variazione**: il 93% dei soggetti PNRR (20.703) e il 94% dei
> beneficiari FTS UE non sono ETS iscritti al RUNTS — sono imprese, università,
> PA. Le metriche precedenti li includevano; ora il driver-first li esclude
> correttamente.

---

*Progetto del [DataCivicLab](https://github.com/dataciviclab) — dati aperti, civic tech, impatto sociale.*
