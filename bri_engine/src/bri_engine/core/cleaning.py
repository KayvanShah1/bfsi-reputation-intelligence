from __future__ import annotations

import hashlib
from numbers import Real
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype


COLUMN_MAP = {
    "Date": "date",
    "URL": "url",
    "Source Name": "source_name",
    "Title": "title",
    "Opening Text": "opening_text",
    "Hit Sentence": "hit_sentence",
    "Driver": "original_driver",
    "Sub driver": "original_sub_driver",
    "Sentiment": "sentiment",
    "Reach": "reach",
}

TEXT_COLUMNS = ["title", "opening_text", "hit_sentence"]


def normalize_whitespace(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).replace("\u00a0", " ")
    text = text.replace("...", " ")
    return re.sub(r"\s+", " ", text).strip()


def normalize_for_key(value: object) -> str:
    text = normalize_whitespace(value).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_sentiment(value: object) -> str:
    text = normalize_for_key(value)
    if text == "positive":
        return "Positive"
    if text == "negative":
        return "Negative"
    return "Neutral"


def parse_dates(values: pd.Series) -> pd.Series:
    general = pd.to_datetime(values, errors="coerce")

    if is_datetime64_any_dtype(values):
        return general

    excel_serial_mask = values.map(
        lambda value: isinstance(value, Real)
        or (isinstance(value, str) and value.strip().isdigit())
    )
    numeric = pd.to_numeric(values.where(excel_serial_mask), errors="coerce")
    from_excel = pd.to_datetime(numeric, unit="D", origin="1899-12-30", errors="coerce")
    return general.mask(excel_serial_mask, from_excel)


def canonicalize_url(value: object) -> str:
    url = normalize_whitespace(value)
    if not url:
        return ""

    try:
        parts = urlsplit(url)
    except ValueError:
        return url.lower().rstrip("/")

    query = [
        (key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=False)
        if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}
    ]
    path = parts.path.rstrip("/") or parts.path
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower().removeprefix("www."),
            path,
            urlencode(query),
            "",
        )
    )


def standardize_records(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.rename(columns=COLUMN_MAP).copy()
    df.insert(0, "source_row_id", raw.index + 2)

    for column in COLUMN_MAP.values():
        if column not in df.columns:
            df[column] = ""

    for column in TEXT_COLUMNS + ["url", "source_name"]:
        df[column] = df[column].map(normalize_whitespace)

    df["date"] = parse_dates(df["date"])
    df["sentiment"] = df["sentiment"].map(normalize_sentiment)
    df["reach"] = pd.to_numeric(df["reach"], errors="coerce")
    df["clean_text"] = (
        df[TEXT_COLUMNS].fillna("").agg(" ".join, axis=1).map(normalize_whitespace)
    )
    return df


def build_content_hash(value: object) -> str:
    normalized = normalize_for_key(value)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def build_dedupe_key(row: pd.Series) -> str:
    normalized_url = canonicalize_url(row.get("url", ""))
    title_key = normalize_for_key(row.get("title", ""))
    text_hash = build_content_hash(row.get("clean_text", ""))
    raw_key = "|".join([normalized_url, title_key, text_hash])
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]


def deduplicate_mentions(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    cleaned = df.copy()
    cleaned["normalized_url"] = cleaned["url"].map(canonicalize_url)
    cleaned["content_hash"] = cleaned["clean_text"].map(build_content_hash)
    cleaned["dedupe_key"] = cleaned.apply(build_dedupe_key, axis=1)

    before = len(cleaned)
    cleaned = cleaned.drop_duplicates(subset=["dedupe_key"], keep="first").reset_index(drop=True)
    return cleaned, before - len(cleaned)
