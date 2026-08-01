# Terzo Settore Intelligence — Makefile
# Struttura: ets/ (intelligence), match/ (operativo), bandi/ (acquisizione).
# Sperimentazioni (dashboard, network, partnership) → branch feat/experiments.
.PHONY: build scan radar latest segnale test clean all

all: build comuni-ets scan

# Costruisce l'hub ETS (da RUNTS + 5x1000 + FTS + RNA + PNRR + OC)
# Arricchisce ETS con temi ANAC dagli oggetti dei bandi partecipati
anac-temi:
	python3 ets/enrich_temi.py

# Risolve le sorgenti (layer Lab locale → cache → GCS) e mostra da dove arriva ogni file
sync-sources:
	python3 ets/resolve_sources.py

# Costruisce la tabella long fatti_ets (driver-first: RUNTS 150k CF → join filtrato)
# Legge in-place dal layer clean Lab; scarica da GCS solo i file che mancano altrove.
fatti-ets:
	mkdir -p data/build
	python3 ets/resolve_sources.py --sql > data/build/fatti_ets.sql
	duckdb < data/build/fatti_ets.sql
	python3 -c "import duckdb; c=duckdb.connect(); r=c.sql(\"SELECT count(*) FROM 'data/fatti_ets.parquet'\").fetchone(); assert 400000 < r[0] < 600000, f'Row count {r[0]} fuori range driver-first (atteso ~485k)'; print(f'✅ {r[0]:,} fatti (driver-first) — OK')"

# Costruisce l'hub ETS: fatti_ets → PIVOT + geografia + temi ANAC
build: fatti-ets anac-temi
	duckdb < ets/build_unified_ets.sql
	rm -f data/temi_anac.parquet
	python3 -c "import duckdb; c=duckdb.connect(); r=c.sql(\"SELECT count(*) FROM 'data/unified_ets.parquet'\").fetchone(); assert 140000 < r[0] < 160000, f'Row count {r[0]} fuori range'; print(f'✅ {r[0]} ETS — integrità OK')"

# Scan completo: bandi → match → report
scan radar: build
	python3 match/reports/scan_completo.py

# Vista latest: bandi operativi in scadenza 60gg
latest:
	python3 match/reports/scan_completo.py --latest

# Report segnale per territorio (da scan già eseguito)
segnale:
	[ -n "$(T)" ] || (echo "Usa: make segnale T=MI [C=Comune]" && exit 1)
	python3 match/reports/scan_completo.py --territorio $(T) $(if $(C),--comune "$(C)",)

# Esporta candidati da contattare per un bando
# make contatta B="BPER"          — CSV top 10
# make contatta B="UEFA" ENRICH=1 — con Google Places (lento)
# make contatta B="BPER" FMT=json
contatta:
	[ -n "$(B)" ] || (echo "Usa: make contatta B='BPER' [TOP=10] [ENRICH=1] [FMT=csv]" && exit 1)
	python3 match/reports/contatta.py --bando "$(B)" --top $(if $(TOP),$(TOP),10) $(if $(ENRICH),--enrich,) $(if $(FMT),--formato $(FMT),) || true

# Scheda ETS: profilo completo per debug
scheda:
	[ -n "$(CF)$(NOME)" ] || (echo "Usa: make scheda CF=02006180364 [OPZIONI=--anac,--match,--benchmark]" && exit 1)
	python3 match/reports/scheda.py $(if $(CF),--cf "$(CF)",) $(if $(NOME),--nome "$(NOME)",) $(if $(OPZIONI),$(OPZIONI),)

# Report ETS: profilo + benchmark + bandi
report:
	[ -n "$(CF)" ] || (echo "Usa: make report CF=02006180364" && exit 1)
	python3 match/reports/scheda.py --cf "$(CF)" --benchmark --match

# Preparazione chiamate lunedì: CSV urgenti + report
lunedi: scan
	python3 match/reports/contatta.py --bando "RIZA" --top 10 --enrich
	python3 match/reports/contatta.py --bando "UEFA" --top 10 --enrich
	python3 match/reports/contatta.py --bando "BPER" --top 10 --enrich
	@echo ""
	@echo "✅ Materiale pronto per lunedì:"
	@echo "   contatta-riza-*.csv  — RIZA (€1M, scade 31/7)"
	@echo "   contatta-uefa-*.csv — UEFA Foundation (scade 3/8)"
	@echo "   contatta-bper-*.csv — BPER (€50k, scade 7/9)"
	@echo "   cruscotto/radar-latest.md — report completo"

# Build/report leggono direttamente da GCS
# I dati 5x1000, FTS, RNA, PNRR sono letti via HTTP da build_unified_ets.sql

# Costruisce dataset aggregato per comune (ETS + ANAC + RdC + reddito)
comuni-ets:
	python3 ets/comuni.py

# Aggregazione bandi
bandi-infobandi:
	python3 bandi/infobandi.py

bandi-info-coop:
	python3 bandi/info_cooperazione.py  # ultime ~200 (10 pagine)

bandi-info-coop-full:
	python3 bandi/info_cooperazione.py --full  # TUTTI (lento)

bandi-indicebandi:
	python3 bandi/indicebandi.py

bandi-indicebandi-full:
	python3 bandi/indicebandi.py --full

bandi: bandi-infobandi bandi-info-coop bandi-indicebandi
	@echo "✅ Bandi aggiornati"

# Test matching (pattern + gold set + sezione + geografia + scan integrity)
test:
	python3 tests/test_match.py

# Test dettagliato
test-verbose:
	python3 tests/test_match.py --verbose

# Pulisce file temporanei
clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -f cruscotto/radar-completo.md cruscotto/radar-latest.md cruscotto/radar-completo.json
	@echo "✅ Pulito"

# Incrocio territoriale: match ETS × contesto comune (reddito, RdC, sport)
# make incrocio TAGS="sport minori" TERR=Lombardia OUT=cruscotto/incrocio.md
incrocio:
	[ -n "$(TAGS)" ] || (echo "Usa: make incrocio TAGS='sport minori' [TERR=Lombardia] [OUT=file.md]" && exit 1)
	python3 match/reports/incrocio.py --tags $(TAGS) $(if $(TERR),--terr $(TERR),) $(if $(OUT),--out $(OUT),)
