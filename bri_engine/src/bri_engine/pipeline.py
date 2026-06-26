from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from bri_engine.core.cleaning import deduplicate_mentions, standardize_records
from bri_engine.core.llm_classifier import classify_mention
from bri_engine.core.relevance import assess_relevance
from bri_engine.core.rule_classifier import RuleClassifier
from bri_engine.core.sources import load_source_mapping, normalize_source_name
from bri_engine.core.theme_extraction import extract_top_terms
from bri_engine.settings import Settings, get_settings


OUTPUT_COLUMNS = [
    "source_row_id",
    "date",
    "source_name",
    "title",
    "opening_text",
    "hit_sentence",
    "url",
    "reach",
    "clean_text",
    "is_relevant",
    "relevance_reason",
    "reputation_driver",
    "sub_driver",
    "sentiment",
    "classification_confidence",
    "classification_reason",
    "classification_source",
    "matched_terms",
    "dedupe_key",
]


def _cache_key(text: str, sentiment: str) -> str:
    raw = f"{text}|{sentiment}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_cache(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_cache(path: Path, cache: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def _maybe_llm_classify(
    row: pd.Series,
    rule_result: dict[str, Any],
    cache: dict[str, dict[str, Any]],
    llm_threshold: float,
    settings: Settings,
) -> dict[str, Any]:
    if rule_result["classification_confidence"] >= llm_threshold:
        return rule_result

    key = _cache_key(str(row["clean_text"]), str(row["sentiment"]))
    if key in cache:
        cached = cache[key]
        cached["classification_source"] = "llm_cache"
        return cached

    llm_result = classify_mention(str(row["clean_text"]), str(row["sentiment"]), settings)
    result = {
        "reputation_driver": llm_result.reputation_driver,
        "sub_driver": llm_result.sub_driver,
        "sentiment": llm_result.sentiment,
        "classification_confidence": round(llm_result.confidence, 2),
        "classification_reason": llm_result.rationale,
        "classification_source": "llm",
        "matched_terms": "",
    }
    cache[key] = result
    return result


def _classify_records(
    df: pd.DataFrame,
    settings: Settings,
    use_llm: bool,
    llm_threshold: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    classifier = RuleClassifier.from_yaml(settings.resolved_taxonomy_path)
    cache = _load_cache(settings.llm_cache_path) if use_llm else {}
    llm_available = use_llm and bool(settings.openrouter_api_key_value)
    llm_failures = 0
    outputs: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        if not row["is_relevant"]:
            outputs.append(
                {
                    "reputation_driver": "",
                    "sub_driver": "",
                    "sentiment": row["sentiment"],
                    "classification_confidence": 0.0,
                    "classification_reason": "Record removed as irrelevant.",
                    "classification_source": "not_relevant",
                    "matched_terms": "",
                }
            )
            continue

        rule_result = classifier.classify(row["clean_text"], row["sentiment"])
        result = {
            "reputation_driver": rule_result.reputation_driver,
            "sub_driver": rule_result.sub_driver,
            "sentiment": rule_result.sentiment,
            "classification_confidence": rule_result.confidence,
            "classification_reason": rule_result.rationale,
            "classification_source": "rule",
            "matched_terms": ", ".join(rule_result.matched_terms),
        }

        if llm_available:
            try:
                result = _maybe_llm_classify(row, result, cache, llm_threshold, settings)
            except Exception:
                llm_failures += 1
                result["classification_source"] = "rule_fallback"

        outputs.append(result)

    if use_llm and cache:
        _write_cache(settings.llm_cache_path, cache)

    result_frame = pd.DataFrame(outputs)
    classified = df.reset_index(drop=True).copy()
    if "sentiment" in result_frame.columns:
        classified["sentiment"] = result_frame.pop("sentiment")
    classified = pd.concat([classified, result_frame], axis=1)
    metadata = {
        "llm_requested": use_llm,
        "llm_available": llm_available,
        "llm_failures": llm_failures,
        "llm_threshold": llm_threshold,
    }
    return classified, metadata


def _prepare_for_export(df: pd.DataFrame) -> pd.DataFrame:
    export = df.copy()
    export["date"] = pd.to_datetime(export["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    export["date"] = export["date"].fillna("")
    export["reach"] = export["reach"].round(0).astype("Int64")
    return export[OUTPUT_COLUMNS]


def run_pipeline(
    settings: Settings | None = None,
    input_path: Path | None = None,
    output_stem: str | None = None,
    use_llm: bool | None = None,
    keep_irrelevant: bool = False,
    llm_threshold: float = 0.58,
) -> dict[str, Any]:
    resolved_settings = settings or get_settings()
    source_path = input_path or resolved_settings.input_path
    if output_stem is not None:
        resolved_settings.output_stem = output_stem

    raw = pd.read_excel(source_path)
    standardized = standardize_records(raw)
    source_mapping = load_source_mapping(resolved_settings.resolved_source_mapping_path)
    standardized["source_name"] = standardized.apply(
        lambda row: normalize_source_name(row["source_name"], row["url"], source_mapping),
        axis=1,
    )
    deduped, duplicates_removed = deduplicate_mentions(standardized)

    relevance = deduped.apply(
        lambda row: assess_relevance(row["clean_text"], row["source_name"], row["title"]),
        axis=1,
    )
    deduped["is_relevant"] = [item.is_relevant for item in relevance]
    deduped["relevance_reason"] = [item.reason for item in relevance]

    llm_requested = resolved_settings.openrouter_enabled if use_llm is None else use_llm
    classified, classifier_metadata = _classify_records(
        deduped,
        settings=resolved_settings,
        use_llm=llm_requested,
        llm_threshold=llm_threshold,
    )

    irrelevant_removed = int((~classified["is_relevant"]).sum())
    exported = classified if keep_irrelevant else classified[classified["is_relevant"]].copy()
    exported = _prepare_for_export(exported)

    resolved_settings.output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    exported.to_csv(resolved_settings.output_csv_path, index=False)
    exported.to_excel(resolved_settings.output_xlsx_path, index=False)
    exported.to_parquet(resolved_settings.output_parquet_path, index=False)

    summary = {
        "source_input": str(source_path),
        "output_csv": str(resolved_settings.output_csv_path),
        "output_xlsx": str(resolved_settings.output_xlsx_path),
        "output_parquet": str(resolved_settings.output_parquet_path),
        "raw_rows": int(len(raw)),
        "deduped_rows": int(len(deduped)),
        "duplicates_removed": int(duplicates_removed),
        "irrelevant_removed": irrelevant_removed,
        "records_written": int(len(exported)),
        "keep_irrelevant": keep_irrelevant,
        "sentiment_distribution": exported["sentiment"].value_counts().to_dict(),
        "driver_distribution": exported["reputation_driver"].value_counts().to_dict(),
        "top_themes": extract_top_terms(exported["clean_text"].dropna().tolist(), n_terms=10),
        **classifier_metadata,
    }
    resolved_settings.summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return summary


def parse_args() -> argparse.Namespace:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run the BFSI reputation intelligence pipeline.")
    parser.add_argument("--input", type=Path, default=settings.input_path)
    parser.add_argument("--output-stem", default=settings.output_stem)
    parser.add_argument("--use-llm", action="store_true")
    parser.add_argument("--keep-irrelevant", action="store_true")
    parser.add_argument("--llm-threshold", type=float, default=0.58)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    summary = run_pipeline(
        settings=settings,
        input_path=args.input,
        output_stem=args.output_stem,
        use_llm=args.use_llm,
        keep_irrelevant=args.keep_irrelevant,
        llm_threshold=args.llm_threshold,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
