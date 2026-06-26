# Methodology and Scoring

## Objective

The workflow converts a raw BFSI digital-mentions workbook into a cleaned, deduplicated,
relevance-filtered, and classified dataset for reputation analysis. The design goal is not to train
a custom model on a small sample. The goal is to produce a defensible, auditable classification
layer that a reviewer can inspect row by row.

The current sample run processes 100 raw rows into 84 relevant classified mentions after
deduplication and relevance filtering.

## Input and Output Contract

Input:

- Primary input: `data/raw/Dataset.xlsx`
- Fallback input: `docs/references/Dataset.xlsx`
- Configuration: `config/taxonomy.yml`, `config/source_mapping.yml`, `.env`

Output:

- `data/processed/classified_mentions.csv`
- `data/processed/classified_mentions.xlsx`
- `data/processed/classified_mentions.parquet`
- `data/processed/pipeline_summary.json`

The dashboard reads the Parquet output first because it is compact and fast for interactive use.
CSV and Excel remain available for review and sharing.

## 1. Configuration and Traceability

All paths and provider settings are managed by `bri_engine.settings.Settings`, a Pydantic Settings
model. This keeps local file paths, taxonomy paths, output names, and OpenRouter configuration out
of the application logic.

Each record preserves `source_row_id`, which points back to the original workbook row number. The
pipeline also writes `pipeline_summary.json` with input path, output paths, row counts, sentiment
distribution, driver distribution, top themes, and LLM metadata.

## 2. Cleaning and Schema Standardization

The raw workbook is normalized into a stable schema:

| Raw field | Processed field |
| --- | --- |
| `Date` | `date` |
| `URL` | `url` |
| `Source Name` | `source_name` |
| `Title` | `title` |
| `Opening Text` | `opening_text` |
| `Hit Sentence` | `hit_sentence` |
| `Sentiment` | `sentiment` |
| `Reach` | `reach` |

Cleaning steps:

- Normalize whitespace and non-breaking spaces.
- Build `clean_text` from title, opening text, and hit sentence.
- Parse native datetimes and Excel serial dates.
- Normalize sentiment to `Positive`, `Neutral`, or `Negative`.
- Coerce reach to numeric values without imputing missing reach.
- Preserve missing dates as blank values in the exported files.

## 3. Source Standardization

Source names are standardized before dashboarding so source filters and charts are meaningful.

The process uses `config/source_mapping.yml` in two passes:

1. Explicit aliases standardize known variants such as publisher spelling differences.
2. Blank source names are inferred from URL domains, for example `play.google.com` to `Play Store`.

Reddit URLs are treated separately so subreddit-level sources can be preserved as
`reddit.com/r/<subreddit>` where available. If no configured mapping is found, the URL host is used;
if the host is missing, the source is marked as `Unknown`.

## 4. URL Canonicalization and Deduplication

Deduplication uses a stable `dedupe_key` built from:

- canonical URL
- normalized title
- hash of normalized `clean_text`

URL canonicalization lowercases scheme and domain, removes `www.`, removes common tracking
parameters such as `utm_*`, `fbclid`, and `gclid`, and trims redundant trailing slashes.

The current workbook has 2 duplicate records removed before classification.

## 5. Relevance Filtering

The relevance filter removes records that do not contain a usable ICICI Prudential, leadership, or
dataset-scoped app/service review signal.

Rows are retained when they contain:

- ICICI Prudential brand variants, such as `icici prudential`, `icici pru`, or `ipru`.
- Leadership references, such as `Sankaran Naren` or `Naren`.
- BFSI reputation context, such as mutual fund, AMC, SIP, NFO, scheme, redemption, KYC, app,
  website, SEBI, complaint, returns, performance, or CIO.
- App or customer-service review signals where the workbook context clearly indicates a BFSI
  experience row.

Rows are removed when they are generic or off-topic, such as education directories, job listings, or
market-list content without a brand, leadership, product, or reputation signal.

The output retains `is_relevant` and `relevance_reason` for auditability. By default, irrelevant
records are excluded from the final exported dataset. They can be retained with
`--keep-irrelevant`.

## 6. Taxonomy Classification

The deterministic classifier uses the project taxonomy encoded in `config/taxonomy.yml`.

| Reputation driver | Sub-driver |
| --- | --- |
| Brand Perception | Thought Leadership |
| Brand Perception | Product Strategy |
| Brand Perception | Brand Visibility & Marketing |
| User Experience | Product & Service Quality |
| User Experience | Customer Support & Complaint Resolution |
| User Experience | Digital & Omnichannel Experience |
| Responsible Business Practices | Regulatory Compliance & Ethical Governance |
| Responsible Business Practices | Social Impact & Community (CSR) |

For each relevant row, the classifier evaluates every sub-driver:

- Single-token keyword match: 1 point.
- Multi-word phrase match: 2 points.
- Highest score wins.
- Ties are resolved with a deterministic priority order for known ambiguity.
- If no exact taxonomy terms match, broad context fallbacks assign a conservative bucket.

The tie-break order gives priority to compliance, complaint/support, digital experience, CSR,
product strategy, product/service quality, thought leadership, and finally brand visibility. This
prevents generic product or brand terms from overriding higher-risk service and compliance signals.

## 7. Confidence Scoring

Confidence is a rule-based interpretability score, not a calibrated probability.

| Case | Confidence behavior |
| --- | --- |
| Empty usable text | `0.30` and broad Product Strategy fallback |
| No exact taxonomy match, contextual fallback used | `0.46` |
| Exact taxonomy matches found | `0.54 + 0.07 * score`, capped at `0.95` |

The exported row includes `classification_reason` and up to eight `matched_terms`, so the user can
see why a driver/sub-driver was selected.

## 8. Sentiment Handling

Sentiment is normalized from the workbook labels. The pipeline does not infer sentiment from text in
the deterministic path. This keeps the classification task focused on reputation driver and
sub-driver identification while preserving the analyst-provided sentiment signal.

## 9. Optional LLM Path

The default workflow is deterministic and does not require network access or an API key.

When `--use-llm` is passed, or `OPENROUTER_ENABLED=true` is set, low-confidence records can be sent
to a Pydantic AI classifier backed by OpenRouter. The LLM result must satisfy the strict Pydantic
schema in `bri_engine.core.schemas`. If the API key is missing, the provider fails, or validation
does not pass, the rule-based result is retained.

LLM results are cached by text and sentiment hash in `data/processed/llm_cache.json` to avoid
repeat calls for the same record.

## 10. Theme Extraction

Dashboard themes are extracted from `clean_text` using TF-IDF. They are intended as directional
discussion topics, not as final taxonomy labels. The taxonomy classification remains the source of
truth for driver and sub-driver reporting.

## Dashboard Interpretation

The dashboard is built for review and exploration:

- KPI cards summarize total records, relevance, sentiment, and leading reputation clusters.
- Monthly mention volume uses stacked sentiment bars, including an `Undated` bucket for records
  without a source date.
- Driver, sub-driver, source, and sentiment charts use readable axis labels and standardized names.
- The sentiment-intensity heatmap highlights where negative and positive records concentrate by
  driver.
- The content explorer exposes the original text, URL, date, source, classification, confidence,
  rationale, and matched terms.

## Assumptions and Limitations

- The dataset is scoped to ICICI Prudential BFSI reputation monitoring.
- App and support review rows with missing source metadata can still be relevant when the text
  clearly describes a BFSI service experience.
- Existing workbook sentiment labels are treated as authoritative after normalization.
- Rule-based classification can miss sarcasm, implicit context, or subtle reputational nuance.
- The small sample dataset is not suitable for training a supervised model.
- The taxonomy and relevance terms should be reviewed before applying the workflow to another
  brand, sector, or geography.
