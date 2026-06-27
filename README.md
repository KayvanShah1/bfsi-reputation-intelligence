# BFSI Reputation Intelligence

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-Workspace-6E56CF)
![Pydantic](https://img.shields.io/badge/Pydantic-Settings%20%2B%20Schemas-E92063?logo=pydantic&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?logo=streamlit&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-Tests-0A9EDC?logo=pytest&logoColor=white)
![Ruff](https://img.shields.io/badge/Ruff-Linting-D7FF64)

![BFSI Reputation Intelligence banner](docs/assets/banner.png)

A compact reputation-intelligence engine for BFSI mentions. It normalizes messy source data,
deduplicates records, filters relevance, assigns explainable reputation drivers, and serves the
result through a Streamlit dashboard.

The project is intentionally small, but shaped like production software: installable package,
versioned config, Pydantic settings, deterministic scoring first, optional LLM fallback, Parquet
serving data, and row-level audit fields.

## Why It Matters

Digital reputation data is messy. The same brand can appear across news snippets, syndicated
articles, app-store reviews, forum-style posts, and low-context web results. Some rows are useful
signals, some are duplicates, and some mention adjacent BFSI terms without saying anything
reputation-relevant.

This project treats reputation intelligence as a controlled analytical workflow rather than a
one-off prompt. Every record moves through schema standardization, source cleanup, deduplication,
relevance filtering, taxonomy classification, export generation, and dashboard exploration.

## Design Principle

The core design principle is separation of language understanding from analytical authority:

- Deterministic logic owns cleaning, deduplication, relevance filtering, and high-confidence
  taxonomy matches.
- Optional LLM classification is reserved for ambiguous or low-confidence records.
- Pydantic schemas constrain model outputs to the approved reputation framework.
- Every classified row keeps audit fields so a reviewer can inspect why a mention received its
  driver, sub-driver, sentiment, and confidence score.

The goal is not to hide uncertainty. The goal is to make classification decisions inspectable.

## Core Capabilities

- Converts raw news, review, and social-style mention records into a stable analytical schema.
- Standardizes inconsistent or missing source names from aliases and URL domains.
- Removes duplicate mentions using canonical URLs, normalized titles, and content hashes.
- Filters records that do not carry a usable brand, leadership, product, service, or reputation
  signal.
- Classifies relevant records into a fixed BFSI reputation taxonomy with confidence, rationale, and
  matched terms.
- Writes CSV, Excel, Parquet, and JSON summary outputs for downstream use.
- Provides an interactive dashboard for sentiment, drivers, source mix, themes, and source evidence.
- Supports optional Pydantic AI classification through OpenRouter for low-confidence records.

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

Equivalent package entry points:

```bash
uv run bri-engine
uv run bri-pipeline
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
| Design doc | [docs/DESIGN.md](docs/DESIGN.md) | System goals, trade-offs, auditability, and production path. |
| Methodology | [docs/methodology.md](docs/methodology.md) | Cleaning, relevance, source normalization, scoring, and caveats. |
| Scale plan | [docs/scalability_approach.md](docs/scalability_approach.md) | Collection, storage, orchestration, governance, and operations. |
| Developer notes | [docs/development.md](docs/development.md) | Package layout, entry points, and extension notes. |

## Architecture Overview

```mermaid
flowchart LR
    A[Raw mentions workbook] --> B[Settings and versioned config]
    B --> C[Schema standardization]
    C --> D[Source normalization]
    D --> E[URL and content deduplication]
    E --> F[Relevance gate]
    F --> G[Deterministic taxonomy scorer]
    G --> H{Low confidence?}
    H -->|No| I[Validated classification]
    H -->|Optional| J[Pydantic AI classifier]
    J --> I
    I --> K[CSV, Excel, Parquet, summary JSON]
    K --> L[Streamlit research dashboard]
```

The default path is deterministic and offline. The OpenRouter-backed LLM path is opt-in and only
useful for low-confidence records where language nuance adds value.

## Classification Contract

Each relevant mention becomes a structured classification record:

```json
{
  "is_relevant": true,
  "reputation_driver": "User Experience",
  "sub_driver": "Digital & Omnichannel Experience",
  "sentiment": "Negative",
  "classification_confidence": 0.82,
  "classification_reason": "Matched app, login, and transaction failure terms.",
  "matched_terms": ["app", "login", "transaction"],
  "classification_source": "rule"
}
```

The dashboard and exports use this contract consistently, so aggregate charts can be traced back to
source text and classification rationale.

## Taxonomy

The classifier maps relevant mentions to three reputation drivers:

| Driver | Sub-drivers |
| --- | --- |
| Brand Perception | Thought Leadership, Product Strategy, Brand Visibility & Marketing |
| User Experience | Product & Service Quality, Customer Support & Complaint Resolution, Digital & Omnichannel Experience |
| Responsible Business Practices | Regulatory Compliance & Ethical Governance, Social Impact & Community (CSR) |

The deterministic classifier uses [config/taxonomy.yml](config/taxonomy.yml) as the source of truth.
This keeps taxonomy changes reviewable without changing Python code.

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

## Dashboard Walkthrough

The Streamlit dashboard is a review surface for reputation signals:

1. Start with KPI cards for total records, relevance, sentiment mix, and leading clusters.
2. Use driver and sub-driver charts to see where the conversation concentrates.
3. Review the sentiment intensity heatmap to find positive and negative clusters by driver.
4. Filter the content explorer by driver, sub-driver, sentiment, source, date range, or keyword.
5. Inspect original title, opening text, hit sentence, URL, rationale, confidence, and matched
   terms before using an insight downstream.

## Validation and Quality Checks

Regression checks cover the highest-risk workflow decisions:

- Product-launch mentions map to `Brand Perception / Product Strategy`.
- App transaction complaints map to `User Experience / Digital & Omnichannel Experience`.
- SEBI and compliance mentions map to `Responsible Business Practices / Regulatory Compliance & Ethical Governance`.
- Generic off-topic records are filtered out as irrelevant.
- Excel serial dates, native datetimes, sentiment labels, duplicate URLs, and source aliases are
  normalized consistently.

Run them with:

```bash
uv run pytest
uv run ruff check .
```

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

## Documentation

- [Design Document](docs/DESIGN.md): system framing, design goals, architecture, auditability, and
  production path.
- [Methodology and Scoring](docs/methodology.md): cleaning, source normalization, deduplication,
  relevance filtering, taxonomy scoring, confidence, and limitations.
- [Scalability Approach](docs/scalability_approach.md): daily collection approach for news, social,
  app stores, storage, orchestration, governance, and observability.
- [Development Notes](docs/development.md): package layout, entry points, extension points, and
  configuration notes.

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
