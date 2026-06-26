import pandas as pd

from bri_engine.core.cleaning import deduplicate_mentions, standardize_records
from bri_engine.core.relevance import assess_relevance
from bri_engine.core.rule_classifier import RuleClassifier
from bri_engine.core.sources import load_source_mapping, normalize_source_name


def test_product_launch_maps_to_product_strategy() -> None:
    classifier = RuleClassifier.from_yaml("config/taxonomy.yml")

    result = classifier.classify(
        "ICICI Prudential Mutual Fund launches a new NFO and index fund offering.",
        "neutral",
    )

    assert result.reputation_driver == "Brand Perception"
    assert result.sub_driver == "Product Strategy"
    assert result.sentiment == "Neutral"
    assert result.confidence >= 0.6


def test_app_transaction_complaint_maps_to_digital_experience() -> None:
    classifier = RuleClassifier.from_yaml("config/taxonomy.yml")

    result = classifier.classify(
        "The app keeps logging out during SIP transactions and fails after login.",
        "Negative",
    )

    assert result.reputation_driver == "User Experience"
    assert result.sub_driver == "Digital & Omnichannel Experience"
    assert result.sentiment == "Negative"


def test_regulatory_mention_maps_to_governance() -> None:
    classifier = RuleClassifier.from_yaml("config/taxonomy.yml")

    result = classifier.classify(
        "SEBI disclosure and compliance questions were raised about governance.",
        "neutral",
    )

    assert result.reputation_driver == "Responsible Business Practices"
    assert result.sub_driver == "Regulatory Compliance & Ethical Governance"


def test_dataset_scoped_app_review_without_brand_is_relevant() -> None:
    result = assess_relevance(
        "The app is pathetic and I cannot login to make a transaction.",
        source_name="Play Store",
        title="Digital Experience",
    )

    assert result.is_relevant


def test_generic_college_directory_record_is_irrelevant() -> None:
    result = assess_relevance(
        "Best MBA colleges in Kalyan with placements and admission details.",
        source_name="Shiksha.com",
        title="Best MBA Colleges in Kalyan",
    )

    assert not result.is_relevant


def test_cleaning_normalizes_sentiment_and_removes_duplicate() -> None:
    raw = pd.DataFrame(
        [
            {
                "Date": 46039,
                "URL": "https://example.com/article?utm_source=test",
                "Source Name": "Example",
                "Title": "ICICI Prudential launches fund",
                "Opening Text": "New NFO",
                "Hit Sentence": "",
                "Driver": "",
                "Sub driver": "",
                "Sentiment": "positive",
                "Reach": "100",
            },
            {
                "Date": 46039,
                "URL": "https://example.com/article",
                "Source Name": "Example",
                "Title": "ICICI Prudential launches fund",
                "Opening Text": "New NFO",
                "Hit Sentence": "",
                "Driver": "",
                "Sub driver": "",
                "Sentiment": "Positive",
                "Reach": "100",
            },
        ]
    )

    standardized = standardize_records(raw)
    deduped, removed = deduplicate_mentions(standardized)

    assert standardized["sentiment"].tolist() == ["Positive", "Positive"]
    assert standardized["date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2026-01-17",
        "2026-01-17",
    ]
    assert removed == 1
    assert len(deduped) == 1


def test_cleaning_preserves_excel_loaded_datetime_values() -> None:
    raw = pd.DataFrame(
        [
            {
                "Date": pd.Timestamp("2026-03-12"),
                "URL": "https://example.com/article",
                "Source Name": "Example",
                "Title": "ICICI Prudential market outlook",
                "Opening Text": "CIO outlook",
                "Hit Sentence": "",
                "Driver": "",
                "Sub driver": "",
                "Sentiment": "neutral",
                "Reach": "100",
            }
        ]
    )

    standardized = standardize_records(raw)

    assert standardized.loc[0, "date"].strftime("%Y-%m-%d") == "2026-03-12"


def test_source_name_can_be_inferred_from_play_store_url() -> None:
    source_mapping = load_source_mapping("config/source_mapping.yml")

    source_name = normalize_source_name(
        "",
        "https://play.google.com/store/apps/details?id=com.iPruAMC&hl=en_IN",
        source_mapping,
    )

    assert source_name == "Play Store"


def test_source_name_aliases_are_standardized() -> None:
    source_mapping = load_source_mapping("config/source_mapping.yml")

    assert normalize_source_name("Moneycontrol.com", "", source_mapping) == "Moneycontrol"
    assert normalize_source_name("newspointapp", "", source_mapping) == "NewsPoint"
