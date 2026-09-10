# Terzo Settore Intelligence — Makefile
# Pipeline toolkit: datasets/ (fetch) + compose/ (fonti) + ets_unified (pivot).
# Bandi: acquisizione separata.

TOOLKIT = toolkit

# Abilita source type `script` del toolkit (download RUNTS WebForms)
export TOOLKIT_ALLOW_SCRIPT_SOURCE ?= 1

# --- Dataset del repo -------------------------------------------------------
DATASETS := $(shell find datasets compose -name dataset.yml 2>/dev/null | sort)

# --- Run toolkit ------------------------------------------------------------

.PHONY: run
run:
	$(TOOLKIT) run --config datasets/runts/dataset.yml
	$(TOOLKIT) run --config datasets/ade-cinque-per-mille/dataset.yml
	$(TOOLKIT) run --config datasets/istat_non_profit_2023/dataset.yml
	$(TOOLKIT) run --config compose/ets_5xmille/dataset.yml
	$(TOOLKIT) run --config compose/ets_anac/dataset.yml
	$(TOOLKIT) run --config compose/ets_pnrr/dataset.yml
	$(TOOLKIT) run --config compose/ets_rna/dataset.yml
	$(TOOLKIT) run --config compose/ets_fts/dataset.yml
	$(TOOLKIT) run --config compose/ets_mef/dataset.yml
	$(TOOLKIT) run --config compose/ets_opencoesione/dataset.yml
	$(TOOLKIT) run --config compose/ets_unified/dataset.yml

.PHONY: run-all
run-all: run

# --- Validazione config ------------------------------------------------------

.PHONY: check
check:
	@for f in $(DATASETS); do \
		echo "→ $$f"; \
		$(TOOLKIT) run preflight --config "$$f" > /dev/null 2>&1 || exit 1; \
	done
	@echo "✅ All configs valid"

# --- Bandi (acquisizione) ---------------------------------------------------

.PHONY: bandi-infobandi bandi-info-coop bandi
bandi-infobandi:
	PYTHONPATH=$(CURDIR) python3 bandi/infobandi.py

bandi-info-coop:
	PYTHONPATH=$(CURDIR) python3 bandi/info_cooperazione.py

bandi: bandi-infobandi bandi-info-coop
	@echo "✅ Bandi aggiornati"

# --- Pipeline completa: toolkit + bandi -------------------------------------

.PHONY: all
all: run bandi

# --- Registry ----------------------------------------------------------------

.PHONY: registry registry-write
registry:
	$(TOOLKIT) registry build --prefix terzo_settore --flat

registry-write:
	$(TOOLKIT) registry build --prefix terzo_settore --flat --write

# --- Pulizia -----------------------------------------------------------------

.PHONY: clean
clean:
	rm -rf out/data/_runs out/data/probe out/data/raw out/data/clean out/data/mart .tmp/

.PHONY: clean-runs
clean-runs:
	rm -rf out/data/_runs/

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:' Makefile | sort
