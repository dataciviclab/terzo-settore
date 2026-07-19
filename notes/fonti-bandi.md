# Fonti bandi — stato e lesson learned

## Fonti attive (3)

| Fonte | Tipo | Accesso | Bandi attivi | Affidabilità |
|---|---|---|---|---|
| [Infobandi](https://infobandi.csvnet.it/) | WordPress REST API | JSON | 52 | Alta — API stabile |
| [Info-cooperazione](https://www.info-cooperazione.it/) | ASP.NET MVC | HTML scraping | 22 | Media — sito cambia URL |
| [IndiceBandi](https://www.indicebandi.it/) | Drupal 9 | RSS + HTML | 2 (TS) | Alta — feed RSS strutturato |

**Totale catalogo attivo**: ~69 bandi unici (dopo dedup per ente+scadenza)

## Cosa abbiamo imparato

### Le fonti sono complementari, non sovrapposte
- **Infobandi**: bandi UE, Ministeri, pochi privati. Budget spesso presente.
- **Info-cooperazione**: fondazioni (Cariplo, San Paolo, PuntoSud), UE, bandi sociali. Il 90% dei bandi è scaduto — serve filtro.
- **IndiceBandi**: Regioni, fondazioni, INAIL. Budget raramente presente nei campi strutturati.
- Zero duplicati tra le 3 dopo il dedup per ente+scadenza.

### Il 70% del catalogo era rumore
Prima del filtro scaduti alla fonte: 295 bandi, di cui 187 scaduti (63%).
Dopo: 69 bandi, zero scaduti.

### I duplicati sono cross-lingua
Stesso bando (es. UEFA) può apparire in italiano su una fonte e inglese su un'altra.
Il dedup per titolo non basta — serve ente + scadenza.

### Info-cooperazione è fragile
- Usa ASP.NET MVC, l'URL delle pagine cambia (era `/bandi/`, ora `/Category/Bandi`)
- Ha Cloudflare con CSP restrittivo
- Fortunatamente ha un campo `scaduto` esplicito → filtro facile

### IndiceBandi ha budget raro
Solo 2/27 bandi avevano budget parsato. I bandi regionali/fondazioni
pubblicano budget solo nella pagina singola, non nel feed RSS.

## Statistiche attuali (18/07/2026)

```
Catalogo:    69 bandi (52 infobandi + 22 info-coop + 2 indicebandi, 7 duplicati rimossi)
Match:       46/47 bandi attivi hanno ETS candidati (97.9%)
Gap:         1 bando senza match (tag non riconosciuti)
Candidature: 920 (20/bando, match_limit)
ETS unici:   302
Score medio: 112 (range 90-138)
Budget:      11/46 bandi con budget noto, €35M totali
```

## Note operative

Gli scraper sono in `bandi/`, ognuno produce un JSON in `data/bandi/`.
Il Makefile ha target specifici (`make bandi-infobandi`, `make bandi-info-coop`,
`make bandi-indicebandi`) e `make bandi` per tutti e tre.

Il matching è in `match/matcher.py`, orchestrato da `match/pipeline.py`.
I report sono in `match/reports/`.

## Da fare / miglioramenti

- [ ] Budget: parsare da pagina singola IndiceBandi (--full option già esiste)
- [ ] Fonte aggiuntiva: Fondazione Cariplo direttamente (ma già coperta)
- [ ] Fonte aggiuntiva: EU Funding & Tenders API (bandi UE strutturati)
- [ ] Monitoraggio salute fonti (alert se info-coop cambia HTML)
