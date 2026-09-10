# Contribuire a Terzo Settore Intelligence

Come contribuire al progetto.

## Flusso

1. **Discussion** → domande, interpretazioni, proposte di metriche
2. **Issue** → bug, problemi tecnici, miglioramenti della pipeline
3. **Pull Request** → modifiche concrete

## Sviluppo locale

```bash
# Setup
pip install -e ".[pipeline,dev]"

# Pipeline
make run

# Validazione
make check

# Test
make test

# Dashboard
pip install -e ".[dashboard]"
streamlit run dashboard/app.py
```

## Convenzioni

- **SQL**: usa le macro standard del toolkit (`normalize_string`, `cast_int`, `decode_flag`, etc.)
- **Dataset YAML**: dichiara sempre `required_columns`, `validate.not_null`, `validate.min_rows`
- **Commit**: messaggi in formato conventional (`feat:`, `fix:`, `refactor:`, etc.)
- **Branch**: `feat/nome-feature`, `fix/nome-bug`

## Struttura dei dataset

Ogni dataset deve avere:
```
datasets/<slug>/
├── dataset.yml          # Config (name, source_id, years, tags, category)
├── sql/
│   ├── clean.sql        # RAW → CLEAN (normalizzazione)
│   └── mart*.sql        # CLEAN → MART (aggregazione)
└── notes.md             # Note tecniche
```

## Checklist PR

- [ ] `make check` passa
- [ ] `make test` passa
- [ ] `dataset.yml` ha tutti i campi obbligatori
- [ ] `clean.sql` usa le macro standard
- [ ] Nessun path hardcoded
- [ ] Nessun file .dati sensibili committato
