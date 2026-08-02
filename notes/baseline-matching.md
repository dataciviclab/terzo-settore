# Baseline matching — branch main (prima del funnel)
Data: 2026-08-01 · Eseguito su branch feat/matching-funnel (dati driver-first)
Metodo: match_bando attuale (pattern OR di tutti i tag + score additivo capacità)

| id | match | top1 | score range | esito |
|---|---|---|---|---|
| sport-bper | SI | FONDAZIONE L'ALBERO DELLA VITA (MI) | 93-98 | FAIL — atteso ANCS sportiva, top1 non ha sport nel nome |
| disabilita-zenit | SI | FONDAZIONE PROGETTO ARCA (MI) | 90-95 | OK (match) ma top1 dubbio (digitale?) |
| cultura-cresce | SI | APS PER LA RICERCA (BO) | 87-93 | OK-ish |
| volontariato-ue | SI | CROCE ROSSA ITALIANA (RM) | 90-103 | OK |
| cariplo-riprogettiamo | SI | APS PER LA RICERCA (BO) | 88-93 | multi-tema ambiguo |
| design-prize | NO | — | — | FAIL — pattern None (tag non mappati) |
| disabilita-vita | SI | FONDAZIONE L'ALBERO DELLA VITA (MI) | 93-98 | OK |
| ambiente-alimenti | SI | FONDAZIONE TELETHON (RM) | 87-90 | DUBBIO — Telethon non è ambiente |
| fondazione-con-il-sud | SI | FONDAZIONE PROGETTO ARCA (MI) | 88-95 | DUBBIO — beni confiscati? |
| giovani-genp | SI | FONDAZIONE L'ALBERO DELLA VITA (MI) | 83-88 | DUBBIO |

Sintesi:
- 10/10 gold producono match (tranne design-prize → 0)
- Albero della Vita appare in top1 in 3/10 bandi diversi (sport, disabilità, giovani) — segnale di non-discriminazione
- Top1 "grandi nazionali ricchi" dominano: Albero Vita, Progetto Arca, Telethon
- Nessun gold verifica la PERTINENZA tematica del top1 (solo "match=true" e nome presente)

Problemi strutturali da risolvere col funnel:
1. pattern OR di tutti i tag → permissivo (es. UEFA: 10.649 ETS = 7%)
2. score additivo → capacità finanziaria domina il tema
3. tag non mappati (design, premi internazionali) → pattern None → zero match
4. nessuna penalità per mancanza di focus sul tema principale
