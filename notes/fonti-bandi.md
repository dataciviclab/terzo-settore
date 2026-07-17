# Fonti bandi aperti per il Terzo Settore

## Attive (integrate nel radar)

| Fonte | Tipo | Accesso | Bandi catturati | Note |
|-------|------|---------|-----------------|------|
| [infobandi.csvnet.it](https://infobandi.csvnet.it/) | WordPress REST + RSS | API JSON | 68 | Aggregatore CSVnet: fondazioni, PA, EU, privati |
| [info-cooperazione.it](https://www.info-cooperazione.it/Category/Bandi) | ASP.NET MVC | HTML scraping | 100+ | Cooperazione internazionale, fondazioni bancarie, 8x1000, AICS, MAECI, EU |
| [open-cooperazione.it](https://www.open-cooperazione.it/web/Scarica-Dati.aspx) | ASP.NET | CSV export (POST) | 1.592 org (84 match ETS) | Registry IATI: bilanci, contatti, progetti |

## Da verificare / future

| Fonte | Tipo | Accesso | Note |
|-------|------|---------|------|
| [Fondazione Con il Sud](https://www.fondazioneconilsud.it/bandi/) | WordPress | API REST | Già coperto da infobandi/info-cooperazione |
| [Fondazione Cariplo](https://www.fondazionecariplo.it/) | Sito | 403 bot | Già coperto da info-cooperazione (4 bandi) |
| [Compagnia San Paolo](https://www.compagniadisanpaolo.it/) | Sito | 404 pagine | Già coperto da info-cooperazione (3 bandi) |
| [CSVnet nazionale](https://www.csvnet.it/) | Joomla | Cookie wall | Potrebbe avere notiziario bandi RSS |
| [EU Funding & Tenders](https://ec.europa.eu/info/funding-tenders/opportunities/portal/) | API | Da verificare | Bandi UE diretti |

## Statistiche attuali (17/07/2026)

```
Bandi totali lordi:    268 (68 infobandi + 200 info-cooperazione)
Bandi unici non scaduti: 48 (dopo deduplicazione + filtro date)
Bandi matchati:         45/48 (94%)
Bandi senza match:       1/48 (2%) — senza pattern tag
ETS matchabili:        55.552 su 150.125 (37%)
ETS unici coinvolti:   164 (nei match)
```

## Cosa abbiamo imparato

- **Nessuna fonte singola basta**: infobandi copre bandi italiani, info-cooperazione copre EU/cooperazione
- **30% dei bandi sono duplicati** tra le due fonti → deduplicazione necessaria
- **Info-cooperazione è archivio storico**: 80/100 bandi sono scaduti, solo 18 validi
- **Open Cooperazione** non è fonte di bandi ma registry organizzativo → arricchisce ETS con contatti e capacità
- **Fondazioni bancarie** (Cariplo, San Paolo, etc.) sono già su info-cooperazione — non serve scraping diretto
