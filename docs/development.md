# Development Notes

## Package Layout

```text
app/
  streamlit_app.py
config/
  source_mapping.yml
  taxonomy.yml
data/
  raw/
    .gitkeep
  processed/
    classified_mentions.csv
    classified_mentions.xlsx
    classified_mentions.parquet
    pipeline_summary.json
bri_engine/
  pyproject.toml
  src/
    bri_engine/
      settings.py
      pipeline.py
      core/
        cleaning.py
        relevance.py
        rule_classifier.py
        llm_classifier.py
        schemas.py
        sources.py
        theme_extraction.py
docs/
  assets/
    banner.png
  DESIGN.md
  methodology.md
  scalability_approach.md
  references/
tests/
  test_rule_classifier.py
```

## Entry Points

The engine package exposes two equivalent console scripts:

```bash
uv run bri-engine
uv run bri-pipeline
```

The module entry point is also available:

```bash
uv run python -m bri_engine.pipeline
```

## Design Notes

- The root project is a `uv` workspace and the reusable logic lives in the installable
  `bri-engine` package.
- `app/streamlit_app.py` imports `bri_engine` as an installed package rather than reaching into a
  loose local `src` directory.
- `bri_engine.settings.Settings` owns path and provider configuration through Pydantic Settings.
- `config/taxonomy.yml` and `config/source_mapping.yml` are intentionally data files so taxonomy
  and source-cleanup changes can be reviewed without editing Python.
- The dashboard reads Parquet first, then falls back to CSV.

## Extension Points

- Add new taxonomy terms in `config/taxonomy.yml`.
- Add source aliases and domain mappings in `config/source_mapping.yml`.
- Tune relevance logic in `bri_engine/core/relevance.py`.
- Add deterministic classifier tests under `tests/`.
- Enable the optional LLM path only after setting `OPENROUTER_ENABLED=true` and
  `OPENROUTER_API_KEY`.
