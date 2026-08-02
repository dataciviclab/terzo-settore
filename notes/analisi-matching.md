# Analisi matching — scoperte chiave (branch feat/matching-funnel)
Data: 2026-08-01

## Difetti verificati del matching attuale

### D1. Pattern OR di tutti i tag → permissivo
- UEFA (sport+minori+inclusione+educazione): 10.649 ETS matchano (7.1%)
- Basta "inclusione" (tag generico) per matchare → i big nazionali entrano sempre
- Fix: tema PRINCIPALE del bando come filtro stretto, altri tag come bonus

### D2. Score additivo → capacità domina il tema
- 5x1000 >100k = +15, capacità alta = +25 (max ~80) vs tema = solo +10
- Risultato: Albero della Vita in top1 di 3/10 gold diversi (sport, disabilità, giovani)
- Fix: capacità come MOLTIPLICATORE della pertinenza, non somma

### D3. Pattern troppo larghi → falsi positivi
- "sport" = (sport|...|asd|polisportiv|sportiv) → ENPA, AUSER, Banca degli Occhi
  matchano "sport" pur non essendo sportivi (match su 'asd'/'sportiv' in altri contesti)
- Fix: word-boundary o pattern più stretti per tag ad alto rumore

### D4. Tag non mappati → zero match (design-prize)
- ['premi internazionali','design','cooperazione'] → pattern None → 0 ETS
- TEMA_PATTERN ha 21 tag, SEZIONI_PER_TAG 31 → 10 tag con sezione ma senza pattern
- 'design' non esiste in TEMA_PATTERN; 'premi internazionali' ≠ 'premi'
- Fix: fallback per tag non mappati + estensione dizionario

### D5. Nessuna penalità per mancanza di focus
- Un ETS "inclusione" in un bando sportivo ha lo stesso bonus tema di uno sportivo
- Fix: tema principale obbligatorio (filtro), non opzionale

## Pool sportivo per capacità (verifica)
- 5.577 ETS matchano tema sport; solo 2.148 hanno capacità media+ (771 alta, 684 medio-alta, 693 media)
- 3.125 hanno capacità "sconosciuta" → se esclusi dal ranking, si perdono piccoli ETS locali sportivi
- Tra i top per 5x1000 spuntano non-sportivi (ENPA, AUSER) → conferma D3

## Dati per il design del funnel
- ETS totali: 150.164
- Con capacità media+: ~60.000 (media 37.5K + medio-alta 19K + alta 4K)
- Pool sportivo con capacità: 2.148 → top-10 selezionabile con margine

## Domande aperte da decidere col design
1. Peso capacità dentro il tema: moltiplicatore 1.0? 0.5? (da tarare sui gold)
2. Escludere capacità "sconosciuta" dal ranking o tenerla in coda?
3. Tag non mappati: estendere dizionario o fallback generico?

## Scoperta aggiuntiva (01/08): dizionario tag troppo rigido

Analisi dei 131 bandi reali:
- 78 tag non mappati su 230 occorrenze totali
- Molti sono SINONIMI non normalizzati:
  - 'inclusione' (32) vs 'inclusione sociale' (22) → stesso tema, 2 nomi
  - 'istruzione' (10) vs 'educazione' (12) → stesso tema
  - 'scuole' (6) vs 'scuola' (2) → stesso tema
  - 'adolescenti' (5) vs 'minori' (15) → stesso tema
  - 'povertà' (4) vs 'inclusione sociale' (22) → correlati
- Tag veri non coperti: turismo (13), sviluppo economico (17), montagna (9),
  agricoltura (9), famiglia (7), smart city (5), energia (4)
- Impatto: design-prize aveva tag tutti non mappati → pattern None → 0 match
- Fix v2: normalizzazione tag (sinonimi → tema canonico) PRIMA del pattern

## Risultati funnel v1 (01/08/2026) — confronto con baseline

### Gold set (10 casi)
| id | baseline top1 | funnel top1 | esito |
|---|---|---|---|
| sport-bper | Albero Vita (non sport) | Unione Sportiva ACLI Torino | RISOLTO |
| disabilita-zenit | Progetto Arca | ANFFAS Trentino | migliorato |
| cultura-cresce | APS Ricerca | Biblioteca Ciechi | migliorato |
| volontariato-ue | Croce Rossa | ENPA | ok |
| cariplo | APS Ricerca | Legambiente | migliorato |
| design-prize | 0 match (bug) | 20 match | RISOLTO |
| disabilita-vita | Albero Vita | ANFFAS | migliorato |
| ambiente-alimenti | Telethon | Legambiente | RISOLTO |
| con-il-sud | Progetto Arca | Caritas | ok |
| giovani-genp | Albero Vita | CE.I.S. | migliorato |

- 9/10 gold passano il criterio (design-prize aggiornato nel gold: ora match=true)
- Albero della Vita NON domina più: appare 0 volte in top1 (prima 3/10)

### Fix implementati
1. temi.py v2: normalizza_tags (sinonimi), tema_principale (priorità: sport>minori),
   pattern con fallback dal testo, 30+ sinonimi nuovi (inclusione, istruzione, design...)
2. funnel.py: 3 stadi (sezione→tema→ranking), capacità come addendo non moltiplicatore,
   temi_anac solo come boost debole (tema_temi_anac=30), gate sezione sul TEMA PRINCIPALE
3. matcher.py match_bando → delega al funnel (compatibilità firma)
4. pipeline.py: passa il testo al funnel, semplificato blocco "nessun pattern"
5. BUG trovato: typo "IMPRESI SOCIALI" (senza E) nel dizionario — gate lavoro/formazione
   non funzionava mai. Corretto a "IMPRESE SOCIALI" (12 occorrenze)
6. gold_bandi.json: design-prize aggiornato (era cristallizzato sul bug 0-match)

### Scan reale (131 bandi)
- match: 54, sin_match: 0 (prima c'era il gap design-prize)
- ETS unici: 389
- Sport in Lombardia: solo vere ASD/APS lombarde
