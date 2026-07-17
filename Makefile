# Terzo Settore Intelligence — Makefile
.PHONY: build scan radar latest segnale test clean clean-cache all

all: build scan

# Costruisce l'hub ETS (da RUNTS + 5x1000 + FTS + RNA + PNRR + OC)
build:
	duckdb < sql/build_unified_ets.sql
	@echo "✅ unified_ets ricostruito"

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

# Build/report leggono direttamente da GCS
# I dati 5x1000, FTS, RNA, PNRR sono letti via HTTP da build_unified_ets.sql

# Aggregazione bandi
bandi-infobandi:
	python3 aggregatori/bandi/infobandi.py

bandi-info-coop:
	python3 aggregatori/bandi/info_cooperazione.py  # ultime ~200 (10 pagine)

bandi-info-coop-full:
	python3 aggregatori/bandi/info_cooperazione.py --full  # TUTTI (lento)

bandi: bandi-infobandi bandi-info-coop
	@echo "✅ Bandi aggiornati"

# Integrazione OC
oc:
	python3 aggregatori/integra_oc.py

# Test matching (pattern + gold set)
test:
	python3 test_match.py

# Test dettagliato
test-verbose:
	python3 test_match.py --verbose

# Pulisce file temporanei
clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -f cruscotto/radar-completo.md cruscotto/radar-latest.md
	@echo "✅ Pulito"

# Pulisce eventuale cache locale legacy. Build/report leggono da GCS.
clean-cache:
	rm -rf data/cache
	@echo "✅ Cache locale rimossa"
