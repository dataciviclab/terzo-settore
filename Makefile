# Terzo Settore Intelligence — Makefile
# Build via toolkit (datasets/ets_unified), schede via CLI tsi.

# Source type `script` del toolkit (download RUNTS WebForms) — abilitato esplicitamente
export TOOLKIT_ALLOW_SCRIPT_SOURCE ?= 1
export TOOLKIT ?= toolkit

# CLI unica (vedi tsi/cli.py)
TSI ?= .venv/bin/python -m tsi

.PHONY: build scheda-ente scheda-bando bandi test clean all

all: build

# ─── Build (toolkit) ────────────────────────────────────────────────
build:
	$(TOOLKIT) run --config datasets/runts/dataset.yml
	$(TOOLKIT) run --config datasets/ets_unified/dataset.yml

# ─── Schede ────────────────────────────────────────────────────────
scheda-ente:
	$(TSI) scheda-ente $(CF)

scheda-bando:
	$(TSI) scheda-bando $(if $(N),--top $(N),) $(ARGS)

list-bandi:
	$(TSI) scheda-bando --list

# ─── Bandi (acquisizione) ──────────────────────────────────────────
bandi-infobandi:
	python3 bandi/infobandi.py

bandi-info-coop:
	python3 bandi/info_cooperazione.py

bandi: bandi-infobandi bandi-info-coop
	@echo "✅ Bandi aggiornati"

# ─── Test ───────────────────────────────────────────────────────────
test:
	python3 tests/test_match.py
