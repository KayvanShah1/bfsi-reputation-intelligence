from __future__ import annotations

from dataclasses import dataclass

from bri_engine.core.cleaning import normalize_for_key


BRAND_TERMS = (
    "icici prudential",
    "icici pru",
    "ipru",
    "prudential mutual fund",
    "icici prudential amc",
    "icici prudential mutual fund",
)

LEADERSHIP_TERMS = (
    "sankaran naren",
    "s naren",
    "naren",
)

STRONG_REPUTATION_CONTEXT = (
    "mutual fund",
    "amc",
    "sip",
    "nfo",
    "scheme",
    "fund manager",
    "portfolio",
    "redemption",
    "kyc",
    "app",
    "website",
    "sebi",
    "customer",
    "complaint",
    "returns",
    "performance",
    "cio",
)

REVIEW_CONTEXT = (
    "play store",
    "mouthshut",
    "digital experience",
    "customer support",
    "app",
    "transaction",
    "login",
    "registration",
    "folio",
    "scheme",
    "sip",
    "nav",
    "portfolio",
    "redemption",
    "lumpsum",
    "amc",
)

IRRELEVANT_CONTEXT = (
    "mba college",
    "colleges",
    "courses fees",
    "admission",
    "entrance exams",
    "placements",
    "job opening",
    "hiring",
)


@dataclass(frozen=True)
class RelevanceResult:
    is_relevant: bool
    reason: str


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def assess_relevance(text: object, source_name: object = "", title: object = "") -> RelevanceResult:
    haystack = " ".join(
        [
            normalize_for_key(source_name),
            normalize_for_key(title),
            normalize_for_key(text),
        ]
    ).strip()

    if not haystack:
        return RelevanceResult(False, "Missing text after cleaning.")

    has_brand = _contains_any(haystack, BRAND_TERMS)
    has_leadership = _contains_any(haystack, LEADERSHIP_TERMS)
    has_reputation_context = _contains_any(haystack, STRONG_REPUTATION_CONTEXT)
    has_review_context = _contains_any(haystack, REVIEW_CONTEXT)

    if not (has_brand or has_leadership):
        if has_review_context and has_reputation_context:
            return RelevanceResult(
                True,
                "Dataset-scoped app or service review retained based on BFSI experience signals.",
            )
        return RelevanceResult(False, "No ICICI Prudential brand or leadership signal found.")

    if _contains_any(haystack, IRRELEVANT_CONTEXT) and not has_reputation_context:
        return RelevanceResult(False, "Brand appears in an unrelated education or directory context.")

    if has_reputation_context:
        return RelevanceResult(True, "Brand mention includes a reputation-relevant BFSI context.")

    return RelevanceResult(True, "Brand mention retained for reputation review.")
