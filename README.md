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

- **Tiene traccia** di 268 bandi da 2 fonti nazionali (Infobandi, Info-cooperazione)
- **Trova gli ETS giusti** per ogni bando, matchando per sezione RUNTS, competenze
  e territorio — non solo per nome
- **Dice chi ha già vinto appalti pubblici** (ANAC: 16.259 ETS con €214 Mld di appalti)
- **Esporta una lista telefonica** CSV con telefono, sito e rating Google, pronta
  da importare in un foglio e iniziare a chiamare

## Esempi d'uso

| Scenario | Comando | Cosa ottieni |
|---|---|---|
| "Bando BPER sport inclusivo, €50k, chi contatto?" | `make contatta B="BPER" ENRICH=1` | 5 ETS sportivi con telefono e sito |
| "Bandi in scadenza questo mese" | `make latest` | 15 bandi urgenti, candidati per ognuno |
| "Comune X ha pochi ETS, possiamo fare qualcosa?" | `make segnale T=MI C=Abbiategrasso` | Landscape ETS + gap sociali |
| "Questo ETS che conosco, a quali bandi può candidarsi?" | `python3 radar/contatta.py --cf 90081250632` | 3 bandi, score 135 ciascuno |
| "Dove c'è domanda pubblica di ETS ma poca offerta?" | `make latest` (sezione gap) | Comuni con appalti riservati e pochi ETS |

## Numeri chiave

| Cosa | Quanto |
|---|---|
| ETS in anagrafe | 150.125 |
| ETS matchabili (capacità media+) | 55.552 |
| Bandi attivi monitorati | 48 |
| Bandi con ETS candidabili | 45 |
| ETS unici nei match | 164 |
| ETS con appalti pubblici ANAC | 16.259 |
| Appalti riservati a ETS (2023-25) | 4.566 |
| Fonti dati integrate | 6 (5x1000, FTS, RNA, PNRR, ANAC, ISTAT) |

## Come iniziare

```bash
git clone ...
cd terzo-settore-intelligence
pip install duckdb requests beautifulsoup4 pandas pyarrow python-dotenv

# Scan completo (bandi → match → CSV contatti)
make scan

# Bandi urgenti
make latest

# Chi contattare per un bando specifico
make contatta B="sport inclusivo" TOP=10

# Con telefono (serve API key Google Maps)
cp .env.example .env  # Inserisci GOOGLE_MAPS_API_KEY
make contatta B="BPER" ENRICH=1
```

## Come funziona

I dati ETS vengono dal **RUNTS** (Ministero del Lavoro) e vengono arricchiti
con capacità progettuale da **5x1000**, **grant UE**, **PNRR** e **aiuti di Stato**,
letti direttamente dal DataCivicLab su Google Cloud Storage.

I bandi arrivano da **Infobandi** (API WordPress) e **Info-cooperazione** (scraping).
Il matching tiene conto di:
- **Sezione RUNTS** (ODV, APS, Impresa Sociale...) come indicatore di pertinenza
- **Denominazione** per match tematico (sport, cultura, disabilità...)
- **Territorio** per circoscrivere la ricerca (bandi locali, Mezzogiorno)
- **Track record** ANAC (appalti pubblici vinti) come segnale di capacità

I contatti arrivano da **Google Places** (opzionale, serve API key).

## Architettura

```
data/
  unified_ets.parquet          Hub ETS: capacità, contatti, flags
  runts_iscritti.parquet       Anagrafe RUNTS
  comuni_ets.parquet           Metriche territoriali (ETS + ANAC + RdC)
  bandi/                       Cache bandi (268 bandi)

radar/
  core.py                      Motore matching e scoring
  scan_completo.py             Scan unico → cache JSON
  bandi-in-scadenza.py         Bandi urgenti (legge cache)
  segnale.py                   Report per territorio (legge cache)
  contatta.py                  CSV contatti (legge cache)

sql/
  build_unified_ets.sql        Costruisce anagrafe ETS
  build_comuni_ets.py          Metriche territoriali
```

## Fonti dati

Tutte pubbliche e riutilizzabili (CC BY 4.0 salvo diversa indicazione):

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

- [x] Matching per sezione RUNTS (bonus per ODV, APS, Imprese Sociali)
- [x] Filtro geografico (bandi locali → solo ETS del territorio)
- [x] Tag puliti (rimossi falsi positivi dalle fonti)
- [x] Gap analysis ANAC (comuni con appalti riservati ma pochi ETS)
- [x] CSV contatti con telefono e sito web
- [ ] Alert automatici (bandi nuovi, scadenze vicine)
- [ ] Refresh settimanale automatico

---

*Progetto del [DataCivicLab](https://github.com/dataciviclab) —
dati aperti, civic tech, impatto sociale.*
