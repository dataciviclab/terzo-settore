# Terzo Settore Intelligence — Makefile
# Build via toolkit (datasets/ets_unified), matching bandi via CLI tsi.

# Source type `script` del toolkit (download RUNTS WebForms) — abilitato esplicitamente
export TOOLKIT_ALLOW_SCRIPT_SOURCE ?= 1
export TOOLKIT ?= toolkit

# CLI unica (vedi tsi/cli.py)
TSI ?= python3 -m tsi

.PHONY: build scan radar latest segnale test clean all

all: build scan

# ─── Build (toolkit) ────────────────────────────────────────────────
# 1. RUNTS snapshot (download WebForms + clean)
# 2. ets_unified: fatti_ets → mart_ets → mart_comuni
build:
	$(TOOLKIT) run --config datasets/runts/dataset.yml
	$(TOOLKIT) run --config datasets/ets_unified/dataset.yml

# ─── Matching bandi ────────────────────────────────────────────────
scan radar:
	$(TSI) scan

latest:
	$(TSI) scan --latest

segnale:
	[ -n "$(T)" ] || (echo "Usa: make segnale T=MI [C=Comune]" && exit 1)
	$(TSI) scan --territorio $(T) $(if $(C),--comune "$(C)",)

pacchetto:
	[ -n "$(T)" ] || (echo "Usa: make pacchetto T=BO (o T=all)" && exit 1)
	$(TSI) pacchetto $(T)

contatta:
	[ -n "$(B)" ] || (echo "Usa: make contatta B='BPER' [TOP=10] [ENRICH=1] [FMT=csv]" && exit 1)
	$(TSI) contatta --bando "$(B)" --top $(if $(TOP),$(TOP),10) $(if $(ENRICH),--enrich,) $(if $(FMT),--formato $(FMT),) || true

scheda:
	[ -n "$(CF)$(NOME)" ] || (echo "Usa: make scheda CF=02006180364 [OPZIONI=--anac,--match,--benchmark]" && exit 1)
	$(TSI) scheda $(if $(CF),--cf "$(CF)",) $(if $(NOME),--nome "$(NOME)",) $(if $(OPZIONI),$(OPZIONI),)

report:
	[ -n "$(CF)" ] || (echo "Usa: make report CF=02006180364" && exit 1)
	$(TSI) scheda --cf "$(CF)" --benchmark --match

lunedi: scan
	$(TSI) contatta --bando "RIZA" --top 10 --enrich
	$(TSI) contatta --bando "UEFA" --top 10 --enrich
	$(TSI) contatta --bando "BPER" --top 10 --enrich
	@echo ""
	@echo "✅ Materiale pronto per lunedì"

# ─── Bandi (acquisizione) ──────────────────────────────────────────
bandi-infobandi:
	python3 bandi/infobandi.py

bandi-info-coop:
	python3 bandi/info_cooperazione.py

bandi-info-coop-full:
	python3 bandi/info_cooperazione.py --full

bandi: bandi-infobandi bandi-info-coop
	@echo "✅ Bandi aggiornati"

# ─── Test ───────────────────────────────────────────────────────────
test:
	python3 tests/test_match.py

test-verbose:
	python3 tests/test_match.py --verbose

# ─── Cleanup ────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -f cruscotto/radar-completo.md cruscotto/radar-completo.json
	rm -f cruscotto/radar-latest.md cruscotto/radar-latest.json
	rm -f cruscotto/segnale-*.md cruscotto/segnale-*.json
	@echo "✅ Pulito"
