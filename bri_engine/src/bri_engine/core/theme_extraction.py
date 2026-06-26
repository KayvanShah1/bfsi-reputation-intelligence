from __future__ import annotations

from collections.abc import Iterable

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer


DOMAIN_STOP_WORDS = {
    "icici",
    "prudential",
    "mutual",
    "fund",
    "funds",
    "amc",
    "said",
    "says",
    "india",
    "indian",
    "https",
    "www",
    "com",
}


def extract_top_terms(texts: Iterable[str], n_terms: int = 10) -> list[dict[str, float]]:
    documents = [text for text in texts if isinstance(text, str) and text.strip()]
    if not documents:
        return []

    stop_words = sorted(set(ENGLISH_STOP_WORDS) | DOMAIN_STOP_WORDS)
    vectorizer = TfidfVectorizer(
        stop_words=stop_words,
        ngram_range=(1, 2),
        max_df=0.9,
        min_df=1,
    )
    matrix = vectorizer.fit_transform(documents)
    scores = matrix.sum(axis=0).A1
    terms = vectorizer.get_feature_names_out()
    ranked = sorted(zip(terms, scores, strict=False), key=lambda item: item[1], reverse=True)
    return [{"term": term, "score": round(float(score), 3)} for term, score in ranked[:n_terms]]
