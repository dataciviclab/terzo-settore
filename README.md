# Terzo Settore Intelligence

**Da un bando a una lista di numeri di telefono in due comandi.**

Uno strumento per chi lavora con il Terzo Settore e ha bisogno di sapere,
concretamente, **chi candidare a quale bando, e come contattarlo**.

Non produce report. Produce **lead**.

## Perché esiste

In Italia ci sono **150.000 enti del Terzo Settore (ETS)** iscritti al RUNTS
e **decine di bandi aperti** ogni mese — fondazioni, enti pubblici, programmi UE.

Il problema non è la mancanza di fondi. È la **mancanza di connessione** tra
chi eroga e chi può ricevere. Questo strumento prova a ridurre quel gap.

## Cosa fa

- **Tiene traccia** di 69 bandi da 3 fonti (Infobandi, Info-cooperazione, IndiceBandi)
- **Filtra il rumore**: bandi scaduti e notizie vengono scartati alla fonte
- **Trova gli ETS giusti** per ogni bando, matchando per sezione RUNTS, competenze
  e territorio — non solo per nome
- **Dice chi ha già vinto appalti pubblici** (ANAC: 16.259 ETS con €214 Mld di appalti)
- **Esporta una lista telefonica** CSV con telefono, sito e rating Google, pronta
  da importare in un foglio e iniziare a chiamare

## Esempi d'uso

| Scenario | Comando | Cosa ottieni |
|---|---|---|
| "Bando RIZA da €1M, chi contatto?" | `make contatta B="RIZA" ENRICH=1` | 10 ETS con telefono, scade tra 13gg |
| "Bandi urgenti questa settimana" | `make latest` | Bandi in scadenza + TOP opportunità |
| "Bando BPER sport inclusivo" | `make contatta B="BPER" ENRICH=1` | 10 ETS sportivi con telefono e sito |
| "Comune X ha pochi ETS?" | `make segnale T=MI C=Abbiategrasso` | Landscape ETS + gap sociali |
| "Questo ETS a quali bandi può candidarsi?" | `python3 match/reports/contatta.py --cf 90081250632` | Bandi matchati con score |
| "Tutto pronto per lunedì" | `make lunedi` | Scan + CSV RIZA/UEFA/BPER |

## Numeri chiave (funnel)

| Fase | KPI | Valore |
|---|---|---|
| Catalogo | Bandi attivi | **69** (3 fonti) |
| | Budget totale coperto | **€35M** |
| Matching | Candidature generate | **920** |
| | ETS unici matchati | **302** |
| | Candidati medi per bando | **20** |
| Profilo ETS | Con 5x1000 | **89.7%** |
| | Con appalti ANAC | **85.2%** |
| | Con grant UE | **28.4%** |

## Come iniziare

```bash
git clone https://github.com/dataciviclab/terzo-settore-intelligence.git
cd terzo-settore-intelligence
pip install duckdb requests beautifulsoup4 pandas pyarrow python-dotenv matplotlib

# Scan completo (bandi → match)
make scan

# Bandi urgenti + TOP opportunità
make latest

# Chi contattare per un bando specifico
make contatta B="RIZA" TOP=10

# Con telefono (serve API key Google Maps)
cp .env.example .env  # Inserisci GOOGLE_MAPS_API_KEY
make contatta B="RIZA" ENRICH=1

# Preparazione chiamate
make lunedi
```

## Come funziona

I dati ETS vengono dal **RUNTS** (Ministero del Lavoro) e vengono arricchiti
con capacità progettuale da **5x1000**, **grant UE**, **PNRR** e **aiuti di Stato**,
letti direttamente dal DataCivicLab su Google Cloud Storage.

I bandi arrivano da **3 fonti** complementari:
- **Infobandi** (API WordPress) — bandi UE, Ministeri, privati
- **Info-cooperazione** (HTML scraping) — bandi Terzo Settore, fondazioni
- **IndiceBandi** (RSS + HTML) — bandi Regioni, Fondazioni

Il matching tiene conto di:
- **Sezione RUNTS** (ODV, APS, Impresa Sociale...) come indicatore di pertinenza
- **Denominazione** per match tematico (sport, cultura, disabilità...)
- **Territorio** per circoscrivere la ricerca (bandi locali, Mezzogiorno)
- **Track record** ANAC (appalti pubblici vinti) come segnale di capacità

I contatti arrivano da **Google Places** (opzionale, serve API key).

## Architettura

Il codice è organizzato in 3 layer, uno per fase della pipeline:

```
data/
  unified_ets.parquet         Hub ETS: capacità, profili, temi (25 colonne)
  comuni_ets.parquet          Metriche territoriali (ETS + ANAC + RdC)
  bandi/*.json                Cache bandi (3 fonti, deduplicati)

bandi/                        ← Acquisizione bandi
  infobandi.py                → data/bandi/infobandi_bandi.json
  info_cooperazione.py        → data/bandi/info_cooperazione_bandi.json
  indicebandi.py              → data/bandi/indicebandi_bandi.json

ets/                          ← Costruzione anagrafe ETS
  build_unified_ets.sql       Incrocia RUNTS + 5x1000 + FTS + RNA + PNRR + ANAC
  enrich_temi.py              NLP su oggetti ANAC → temi_anac
  comuni.py                   Metriche aggregate per comune
  match_ets.sql               Template SQL per il matching (condiviso)

match/                        ← Matching bandi ↔ ETS
  matcher.py                  Motore: match_bando, classify_bando, normalise
  pipeline.py                 Orchestrazione: load_bandi, elabora_bando, run_scan
  reports/
    contatta.py               CSV contatti con telefono/sito
    segnale.py                Report per territorio
    scheda.py                 Profilo singolo ETS
    scadenza.py               Bandi urgenti + TOP opportunità
    scan_completo.py          Scan unico → cruscotto/radar-completo.json/md

lib/                          ← Utility condivise
  config.py                   Path, soglie, geografia, date utils
  temi.py                     Keyword → tag tematici, sezioni RUNTS
  format.py                   Formattazione risultati (fmt_euro, fmt_match_reason...)
  html_utils.py               Fallback HTML per budget e testo NLP
  places.py                   Google Places enrichment

tests/
  test_match.py               Test matching: pattern, gold set, sezione, geografia
```

## Fonti dati

| Dataset | Cosa contiene |
|---|---|
| RUNTS | 150k ETS — anagrafe, sezione, sede |
| 5x1000 | Donazioni 2023-2025 — capacità fundraising |
| FTS EU Grants | Grant UE erogati — esperienza europea |
| RNA | Aiuti di Stato — contributi pubblici |
| PNRR | Progetti PNRR — capacità su fondi Next Gen EU |
| ANAC bandi gara | Appalti riservati a ETS/cooperative sociali |
| ANAC aggiudicazioni | Importi e vincitori di appalti pubblici |
| ISTAT comuni | Demografia, redditi, popolazione |
| INPS RdC | Nuclei percettori (2020) |
| Google Places | Sito, telefono, rating |

## Roadmap

- [x] Matching per sezione RUNTS + keyword + territorio
- [x] Tag puliti (rimossi falsi positivi dalle fonti)
- [x] Catalogo bandi multi-fonte (3 fonti)
- [x] Filtro bandi scaduti alla fonte
- [x] Dedup cross-fonte per ente+scadenza
- [x] Gap analysis ANAC (comuni con appalti ma pochi ETS)
- [x] CSV contatti con telefono, sito, rating
- [x] Messaggio personalizzato per chiamata
- [x] Bonus ANAC e 5x1000 nel matching
- [x] Match_limit 20, filtro capacità rilassato
- [ ] Feedback loop (stato contatto: chiamato/interessato/candidato)
- [ ] Refresh automatico settimanale

---

*Progetto del [DataCivicLab](https://github.com/dataciviclab) —
dati aperti, civic tech, impatto sociale.*
