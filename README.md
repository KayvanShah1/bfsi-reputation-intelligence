# BFSI Reputation Intelligence

![BFSI Reputation Intelligence banner](docs/assets/banner.png)

A compact reputation-intelligence engine for BFSI mentions. It normalizes messy source data,
deduplicates records, filters relevance, assigns explainable reputation drivers, and serves the
result through a Streamlit dashboard.

The project is intentionally small, but shaped like production software: installable package,
versioned config, Pydantic settings, deterministic scoring first, optional LLM fallback, Parquet
serving data, and row-level audit fields.

## What It Does

- Converts raw news, review, and social-style mention records into a stable analytical schema.
- Standardizes inconsistent or missing source names from aliases and URL domains.
- Removes duplicate mentions using canonical URLs, normalized titles, and content hashes.
- Filters records that do not carry a usable brand, leadership, product, service, or reputation
  signal.
- Classifies relevant records into a fixed BFSI reputation taxonomy with confidence, rationale, and
  matched terms.
- Writes CSV, Excel, Parquet, and JSON summary outputs for downstream use.
- Provides an interactive dashboard for sentiment, drivers, source mix, themes, and source evidence.

## Current Sample Run

| Measure | Result |
| --- | ---: |
| Raw rows analyzed | 100 |
| Duplicate rows removed | 2 |
| Irrelevant rows removed | 14 |
| Relevant mentions classified | 84 |
| Positive / Neutral / Negative | 28 / 46 / 10 |
| Leading driver | Brand Perception, 48 mentions |
| Largest negative cluster | User Experience, 10 mentions |

## Quick Start

Install the workspace:

```bash
uv sync --all-packages
```

Run the pipeline:

```bash
uv run python -m bri_engine.pipeline
```

Launch the dashboard:

```bash
uv run streamlit run app/streamlit_app.py
```

Run checks:

```bash
uv run pytest
uv run ruff check .
```

## Generated Artifacts

| Artifact | Path | Notes |
| --- | --- | --- |
| Dashboard | [app/streamlit_app.py](app/streamlit_app.py) | Streamlit UI for KPIs, charts, filters, and content exploration. |
| Parquet data | [data/processed/classified_mentions.parquet](data/processed/classified_mentions.parquet) | Preferred dashboard input for compact, fast reads. |
| CSV data | [data/processed/classified_mentions.csv](data/processed/classified_mentions.csv) | Portable classified dataset. |
| Excel data | [data/processed/classified_mentions.xlsx](data/processed/classified_mentions.xlsx) | Spreadsheet-friendly export. |
| Run summary | [data/processed/pipeline_summary.json](data/processed/pipeline_summary.json) | Row counts, distributions, output paths, and theme terms. |
| Methodology | [docs/methodology.md](docs/methodology.md) | Cleaning, relevance, source normalization, scoring, and caveats. |
| Scale plan | [docs/scalability_approach.md](docs/scalability_approach.md) | Collection, storage, orchestration, governance, and operations. |
| Developer notes | [docs/development.md](docs/development.md) | Package layout, entry points, and extension notes. |

## Pipeline Shape

```mermaid
flowchart LR
    A[Raw workbook] --> B[Pydantic settings]
    B --> C[Cleaning]
    C --> D[Source normalization]
    D --> E[Deduplication]
    E --> F[Relevance filter]
    F --> G[Taxonomy scorer]
    G --> H[Optional LLM fallback]
    H --> I[CSV, Excel, Parquet]
    I --> J[Streamlit dashboard]
```

The default path is deterministic and offline. The LLM path is opt-in and only useful for
low-confidence records once OpenRouter is configured.

## Taxonomy

The classifier maps relevant mentions to three reputation drivers:

| Driver | Sub-drivers |
| --- | --- |
| Brand Perception | Thought Leadership, Product Strategy, Brand Visibility & Marketing |
| User Experience | Product & Service Quality, Customer Support & Complaint Resolution, Digital & Omnichannel Experience |
| Responsible Business Practices | Regulatory Compliance & Ethical Governance, Social Impact & Community (CSR) |

Every classified row keeps the fields needed for audit:

- `reputation_driver`
- `sub_driver`
- `sentiment`
- `classification_confidence`
- `classification_reason`
- `matched_terms`
- `classification_source`
- `is_relevant`
- `relevance_reason`
- `dedupe_key`

Sentiment is normalized from the source data. The deterministic classifier is responsible for driver
and sub-driver selection.

## Configuration

Runtime settings are centralized in `bri_engine.settings.Settings` and can be overridden through
`.env`.

```bash
cp .env.example .env
```

Common settings:

| Variable | Default |
| --- | --- |
| `BRI_RAW_DATA_DIR` | `data/raw` |
| `BRI_RAW_DATASET_NAME` | `Dataset.xlsx` |
| `BRI_REFERENCE_INPUT_PATH` | `docs/references/Dataset.xlsx` |
| `BRI_PROCESSED_DATA_DIR` | `data/processed` |
| `BRI_TAXONOMY_PATH` | `config/taxonomy.yml` |
| `BRI_SOURCE_MAPPING_PATH` | `config/source_mapping.yml` |
| `BRI_OUTPUT_STEM` | `classified_mentions` |

Optional OpenRouter settings:

| Variable | Default |
| --- | --- |
| `OPENROUTER_ENABLED` | `false` |
| `OPENROUTER_API_KEY` | blank |
| `OPENROUTER_MODEL` | `openrouter/free` |
| `OPENROUTER_TIMEOUT_SECONDS` | `30` |
| `OPENROUTER_TEMPERATURE` | `0` |
| `OPENROUTER_MAX_TOKENS` | `500` |
| `OPENROUTER_RETRIES` | `1` |

## Data Notes

The pipeline prefers `data/raw/Dataset.xlsx` when present and falls back to
`docs/references/Dataset.xlsx` for reproducible local runs. Raw files under `data/raw/` are ignored
except for `.gitkeep`; processed outputs are kept because they are part of the working analytical
surface.

## Disclaimer

This project is an analytical prototype, not a production compliance, investment-advice, or risk
decisioning system. Classification results are explainable but heuristic, sentiment labels depend on
the source data provided, and any operational use should include source licensing review, privacy
review, human QA, and domain-specific validation.
