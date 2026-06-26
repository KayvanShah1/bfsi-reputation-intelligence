# Data Collection and Scalability Approach

## Target Operating Model

The production version should behave like a monitored reputation-intelligence pipeline, not a
one-off scraper. It should collect source data daily, preserve immutable raw payloads, process
mentions through versioned enrichment steps, and serve a curated analytical layer to dashboards and
alerts.

The core principles are:

- Use approved source APIs or licensed providers where possible.
- Keep raw data immutable and replayable.
- Separate ingestion, enrichment, classification, and serving.
- Version taxonomy, relevance rules, source mappings, and model prompts.
- Route expensive LLM work only to records where it adds value.

## Collection Strategy

Use source-specific collectors instead of a single generic crawler.

| Source type | Collection approach | Key metadata |
| --- | --- | --- |
| News and publisher sites | Licensed news APIs, RSS feeds, approved site-specific crawlers, and media-monitoring vendors where terms allow. | Canonical URL, published timestamp, source, author if available, section, crawl timestamp, extraction status. |
| Reddit | Official Reddit API for subreddit search, keyword monitoring, and post/comment expansion where required. | Post/comment id, subreddit, permalink, score, timestamp, query, pagination cursor. |
| X/Twitter | Official X API or an approved social-listening provider. Use frequent keyword, handle, and cashtag queries to avoid window gaps. | Post id, author metadata allowed by policy, engagement counts, permalink, timestamp, query, collection window. |
| App stores and review sites | Official feeds/APIs where available, otherwise compliant lightweight collectors. | Rating, review id, app/product id, version if available, timestamp, reviewer metadata allowed by policy. |

Each collector should maintain source-specific state: last successful run, pagination cursor,
last-seen ids, rate-limit status, retry count, and extraction quality flags.

## Reference Architecture

```text
Source APIs / feeds / crawlers
        |
        v
Raw object store, partitioned by source and ingestion date
        |
        v
Queue or orchestration layer
        |
        v
Normalization, extraction, language detection, source mapping
        |
        v
Deduplication, relevance filtering, entity tagging
        |
        v
Deterministic taxonomy classifier, optional LLM fallback
        |
        v
Curated Parquet tables and warehouse marts
        |
        v
Dashboard, alerts, analyst review queue
```

## Storage Model

| Layer | Recommended technology | Purpose |
| --- | --- | --- |
| Raw zone | S3, GCS, Azure Blob, or equivalent object storage | Immutable source payloads and crawl metadata. |
| Processed zone | Partitioned Parquet tables | Cleaned mentions, dedupe keys, relevance outputs, entities, and classification results. |
| Warehouse | BigQuery, Snowflake, Postgres, or DuckDB for smaller deployments | Dashboard-friendly marts and analyst query access. |
| Metadata store | Postgres or orchestration metadata DB | Collector state, source health, run logs, retries, model versions, and rule versions. |
| Cache | Redis or object-backed hash cache | Avoid repeat LLM calls for unchanged text. |

Every processed row should keep pointers to the raw payload, collector run id, source id or URL,
dedupe key, classifier version, taxonomy version, and processing timestamp.

## Processing and Orchestration

For daily monitoring, a scheduled batch design is usually sufficient and more reliable than true
real-time processing.

Recommended components:

- Scheduler: Dagster, Airflow, or Prefect.
- Queue: SQS, Pub/Sub, Kafka, or a managed task queue.
- Workers: Cloud Run, Kubernetes jobs, ECS tasks, or serverless functions.
- Transform layer: pandas or Polars for small to medium batches; Spark or warehouse SQL when volume
  grows.
- Serving layer: Streamlit for analyst exploration; BI tooling or an internal web app for wider
  enterprise distribution.

The system should apply backpressure when API limits, extraction failures, or LLM spend thresholds
are reached. Failed records should move to a dead-letter queue with enough metadata to debug and
replay them.

## Classification at Scale

The deterministic taxonomy classifier should remain the first pass:

- It is cheap, explainable, and stable.
- It provides matched terms and rationale for audit.
- It can be regression-tested when taxonomy changes.

LLM classification should be reserved for:

- Low-confidence records.
- High-reach or high-risk mentions.
- Escalations from analyst review.
- New topics not yet covered by the taxonomy.

Controls for the LLM layer:

- Cache by normalized text hash and sentiment.
- Validate every response with a strict schema.
- Store prompt version, model version, provider, latency, token usage, and cost.
- Fall back to deterministic results on timeout, validation failure, or provider error.
- Sample LLM and rule outputs for periodic human QA.

## Data Quality Controls

Quality checks should run at each stage:

- Required fields: source, timestamp or ingestion timestamp, text, URL or source id.
- Timestamp normalization to UTC.
- URL canonicalization and source-domain validation.
- Empty or unusually short text detection.
- Language detection and routing for translation or exclusion.
- Duplicate and near-duplicate detection across syndication and reposts.
- Source freshness checks and crawl failure alerts.
- Distribution checks for sudden shifts in sentiment, source mix, or driver mix.

Near-duplicate detection should combine URL canonicalization, source ids, normalized title/body
hashes, and similarity matching. Thresholds should be conservative so distinct articles are not
accidentally merged.

## Governance, Privacy, and Compliance

Reputation monitoring touches third-party content and, in social channels, potentially personal
data. A production implementation should include:

- Source terms-of-use review before collection.
- Access controls around raw social payloads.
- Retention policies by source type.
- PII minimization and masking where practical.
- Audit logs for analyst actions and taxonomy changes.
- Clear separation between public content, licensed content, and internal annotations.

## Observability

Operational dashboards should track:

- Collector success rate and latency by source.
- Records collected, retained, deduplicated, and classified.
- Empty extraction rate and parse failure rate.
- Records by source, language, sentiment, driver, and confidence band.
- LLM call count, cost, error rate, validation failure rate, and cache hit rate.
- Freshness of the curated dashboard tables.

Alerts should trigger on source outages, unexpected volume drops, duplicate spikes, schema drift,
LLM spend overruns, and high-severity negative mention spikes.

## Scaling Trade-offs

| Decision | Practical trade-off |
| --- | --- |
| Daily batch vs real time | Daily batch is simpler and usually enough for consulting workflows; real time costs more and requires stricter operations. |
| Official APIs vs crawling | APIs are more stable and compliant but can be costly or limited; crawling needs more maintenance and legal review. |
| Rules first vs LLM first | Rules first is cheaper and auditable; LLM first may catch nuance but adds latency, cost, and reproducibility risk. |
| Exact duplicate vs near duplicate | Exact duplicate removal is safe; near-duplicate removal improves quality but can merge distinct stories if thresholds are aggressive. |
| Streamlit vs enterprise BI | Streamlit is fast for prototypes and analyst tools; enterprise BI is better for access control, scheduled reporting, and broad sharing. |

## Pragmatic Roadmap

Phase 1: harden the local workflow.

- Add regression fixtures for relevance and taxonomy edge cases.
- Add source-mapping QA checks.
- Add dashboard smoke tests against the processed Parquet file.

Phase 2: automate daily ingestion.

- Add source registries, collector state, raw payload storage, and scheduled runs.
- Write processed Parquet partitions by ingestion date and source.
- Add data freshness and failure alerts.

Phase 3: add analyst operations.

- Add review queues for low-confidence and high-risk records.
- Track analyst overrides as labeled feedback.
- Use the feedback to refine taxonomy terms, relevance rules, and LLM prompts.

Phase 4: enterprise hardening.

- Add role-based access, retention policy, cost monitoring, and audit logs.
- Publish curated marts for BI tools.
- Introduce service-level objectives for source coverage, freshness, and classification latency.
