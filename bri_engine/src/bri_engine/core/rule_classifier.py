from __future__ import annotations

import re
from pathlib import Path

import yaml

from bri_engine.core.cleaning import normalize_for_key, normalize_sentiment
from bri_engine.core.schemas import ClassificationResult


PRIORITY = [
    ("Responsible Business Practices", "Regulatory Compliance & Ethical Governance"),
    ("User Experience", "Customer Support & Complaint Resolution"),
    ("User Experience", "Digital & Omnichannel Experience"),
    ("Responsible Business Practices", "Social Impact & Community (CSR)"),
    ("Brand Perception", "Product Strategy"),
    ("User Experience", "Product & Service Quality"),
    ("Brand Perception", "Thought Leadership"),
    ("Brand Perception", "Brand Visibility & Marketing"),
]

FALLBACKS = [
    (
        ("Responsible Business Practices", "Regulatory Compliance & Ethical Governance"),
        ("sebi", "penalty", "regulatory", "compliance", "governance", "mis selling"),
    ),
    (
        ("User Experience", "Customer Support & Complaint Resolution"),
        ("complaint", "redemption", "kyc", "customer care", "support", "helpline"),
    ),
    (
        ("User Experience", "Digital & Omnichannel Experience"),
        ("app", "website", "login", "onboarding", "crash", "digital"),
    ),
    (
        ("Responsible Business Practices", "Social Impact & Community (CSR)"),
        ("csr", "financial literacy", "community", "donation", "rural", "outreach"),
    ),
    (
        ("Brand Perception", "Product Strategy"),
        ("launch", "nfo", "offering", "index fund", "new fund", "scheme"),
    ),
    (
        ("User Experience", "Product & Service Quality"),
        ("returns", "performance", "benchmark", "outperformed", "risk", "crore"),
    ),
    (
        ("Brand Perception", "Thought Leadership"),
        ("cio", "naren", "expert", "view", "outlook", "explains", "interview"),
    ),
]


def _priority_index(driver: str, sub_driver: str) -> int:
    try:
        return PRIORITY.index((driver, sub_driver))
    except ValueError:
        return len(PRIORITY)


def _keyword_matches(keyword: str, text: str) -> bool:
    normalized = normalize_for_key(keyword)
    if not normalized:
        return False
    if " " in normalized:
        return normalized in text
    return re.search(rf"\b{re.escape(normalized)}\b", text) is not None


def _keyword_weight(keyword: str) -> int:
    return 2 if " " in normalize_for_key(keyword) else 1


class RuleClassifier:
    def __init__(self, taxonomy: dict[str, dict[str, dict[str, list[str]]]]) -> None:
        self.taxonomy = taxonomy

    @classmethod
    def from_yaml(cls, path: str | Path) -> "RuleClassifier":
        with Path(path).open("r", encoding="utf-8") as handle:
            taxonomy = yaml.safe_load(handle) or {}
        return cls(taxonomy)

    def classify(self, text: object, existing_sentiment: object = None) -> ClassificationResult:
        normalized_text = normalize_for_key(text)
        sentiment = normalize_sentiment(existing_sentiment)

        if not normalized_text:
            return ClassificationResult(
                is_relevant=True,
                reputation_driver="Brand Perception",
                sub_driver="Product Strategy",
                sentiment=sentiment,
                confidence=0.3,
                rationale="Insufficient text; assigned to a broad product strategy bucket.",
                matched_terms=[],
            )

        candidates: list[tuple[int, str, str, list[str]]] = []
        for driver, sub_drivers in self.taxonomy.items():
            for sub_driver, config in sub_drivers.items():
                keywords = config.get("keywords", []) if isinstance(config, dict) else []
                matched_terms = [
                    keyword for keyword in keywords if _keyword_matches(keyword, normalized_text)
                ]
                score = sum(_keyword_weight(keyword) for keyword in matched_terms)
                candidates.append((score, driver, sub_driver, matched_terms))

        score, driver, sub_driver, matched_terms = sorted(
            candidates,
            key=lambda item: (-item[0], _priority_index(item[1], item[2])),
        )[0]

        if score == 0:
            driver, sub_driver, matched_terms = self._fallback(normalized_text)
            reason = (
                f"No exact taxonomy phrase matched; assigned to {sub_driver} from broad "
                "context rules."
            )
            confidence = 0.46
        else:
            reason = f"Matched taxonomy terms for {sub_driver}: {', '.join(matched_terms[:5])}."
            confidence = min(0.95, 0.54 + (0.07 * min(score, 6)))

        return ClassificationResult(
            is_relevant=True,
            reputation_driver=driver,
            sub_driver=sub_driver,
            sentiment=sentiment,
            confidence=round(confidence, 2),
            rationale=reason,
            matched_terms=matched_terms[:8],
        )

    def _fallback(self, normalized_text: str) -> tuple[str, str, list[str]]:
        for (driver, sub_driver), terms in FALLBACKS:
            matched = [term for term in terms if term in normalized_text]
            if matched:
                return driver, sub_driver, matched
        return "Brand Perception", "Product Strategy", []
