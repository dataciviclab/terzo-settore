# Terzo Settore Intelligence — Makefile
# Il package tsi/ è la fonte di verità. radar/ e lib/ sono wrapper backward-compat.
.PHONY: build scan radar latest segnale test monitor clean clean-cache all

all: build comuni-ets scan

# Costruisce l'hub ETS (da RUNTS + 5x1000 + FTS + RNA + PNRR + OC)
build:
	duckdb < sql/build_unified_ets.sql
	python3 -c "import duckdb; c=duckdb.connect(); r=c.sql(\"SELECT count(*) FROM 'data/unified_ets.parquet'\").fetchone(); assert 140000 < r[0] < 160000, f'Row count {r[0]} fuori range'; print(f'✅ {r[0]} ETS — integrità OK')"

# Scan completo: bandi → match → report
scan radar:
	python3 radar/scan_completo.py

# Vista latest: bandi operativi in scadenza 60gg
latest:
	python3 radar/bandi-in-scadenza.py

# Report segnale per territorio
segnale:
	[ -n "$(T)" ] || (echo "Usa: make segnale T=MI [C=Comune]" && exit 1)
	python3 radar/segnale.py --territorio $(T) $(if $(C),--comune "$(C)",)

# Esporta candidati da contattare per un bando
# make contatta B="BPER"          — CSV top 10
# make contatta B="UEFA" ENRICH=1 — con Google Places (lento)
# make contatta B="BPER" FMT=json
contatta:
	[ -n "$(B)" ] || (echo "Usa: make contatta B='BPER' [TOP=10] [ENRICH=1] [FMT=csv]" && exit 1)
	python3 radar/contatta.py --bando "$(B)" --top $(if $(TOP),$(TOP),10) $(if $(ENRICH),--enrich,) $(if $(FMT),--formato $(FMT),) || true

# Monitoraggio salute fonti
monitor:
	python3 -m tsi.monitor.fonti

# Report 20/80: bandi attivi prioritari per budget+urgenza
opportunita:
	python3 radar/opportunita.py $(if $(TOP),--top $(TOP),) $(if $(TAG),--tag $(TAG),)

# Preparazione chiamate lunedì: CSV urgenti + report
lunedi: scan
	python3 radar/contatta.py --bando "RIZA" --top 10 --enrich
	python3 radar/contatta.py --bando "UEFA" --top 10 --enrich
	python3 radar/contatta.py --bando "BPER" --top 10 --enrich
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
	python3 sql/build_comuni_ets.py

# Aggregazione bandi
bandi-infobandi:
	python3 aggregatori/bandi/infobandi.py

bandi-info-coop:
	python3 aggregatori/bandi/info_cooperazione.py  # ultime ~200 (10 pagine)

bandi-info-coop-full:
	python3 aggregatori/bandi/info_cooperazione.py --full  # TUTTI (lento)

bandi-indicebandi:
	python3 aggregatori/bandi/indicebandi.py

bandi-indicebandi-full:
	python3 aggregatori/bandi/indicebandi.py --full

bandi: bandi-infobandi bandi-info-coop bandi-indicebandi
	@echo "✅ Bandi aggiornati"

# Test matching (pattern + gold set + sezione + geografia + scan integrity)
test:
	python3 test_match.py

# Test dettagliato
test-verbose:
	python3 test_match.py --verbose

# Pulisce file temporanei
clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -f cruscotto/radar-completo.md cruscotto/radar-latest.md cruscotto/radar-completo.json
	@echo "✅ Pulito"

# Pulisce eventuale cache locale legacy. Build/report leggono da GCS.
clean-cache:
	rm -rf data/cache
	@echo "✅ Cache locale rimossa"
