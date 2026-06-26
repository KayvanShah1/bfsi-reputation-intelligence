from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

import yaml

from bri_engine.core.cleaning import normalize_for_key, normalize_whitespace


DEFAULT_SOURCE_MAPPING = {
    "source_aliases": {},
    "domain_sources": {
        "play.google.com": "Play Store",
        "google.com": "Play Store",
        "reddit.com": "Reddit",
    },
}


def load_source_mapping(path: str | Path | None) -> dict[str, dict[str, str]]:
    if path is None or not Path(path).exists():
        return DEFAULT_SOURCE_MAPPING
    with Path(path).open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    return {
        "source_aliases": loaded.get("source_aliases", {}) or {},
        "domain_sources": loaded.get("domain_sources", {}) or {},
    }


def _hostname(url: object) -> str:
    cleaned_url = normalize_whitespace(url)
    if not cleaned_url:
        return ""
    try:
        host = urlsplit(cleaned_url).netloc.lower()
    except ValueError:
        return ""
    return host.removeprefix("www.")


def _reddit_source_from_url(url: object) -> str:
    cleaned_url = normalize_whitespace(url)
    if not cleaned_url:
        return ""
    try:
        parts = urlsplit(cleaned_url)
    except ValueError:
        return ""
    path_parts = [part for part in parts.path.split("/") if part]
    if len(path_parts) >= 2 and path_parts[0].lower() == "r":
        return f"reddit.com/r/{path_parts[1]}"
    return ""


def _source_from_domain(url: object, domain_sources: dict[str, str]) -> str:
    host = _hostname(url)
    if not host:
        return ""

    reddit_source = _reddit_source_from_url(url)
    if reddit_source:
        return reddit_source

    for domain, source_name in domain_sources.items():
        normalized_domain = domain.lower().removeprefix("www.")
        if host == normalized_domain or host.endswith(f".{normalized_domain}"):
            return source_name
    return ""


def normalize_source_name(
    source_name: object,
    url: object,
    source_mapping: dict[str, dict[str, str]] | None = None,
) -> str:
    mapping = source_mapping or DEFAULT_SOURCE_MAPPING
    aliases = mapping.get("source_aliases", {})
    domain_sources = mapping.get("domain_sources", {})

    cleaned_source = normalize_whitespace(source_name)
    if cleaned_source:
        alias_lookup = {normalize_for_key(key): value for key, value in aliases.items()}
        return alias_lookup.get(normalize_for_key(cleaned_source), cleaned_source)

    inferred_source = _source_from_domain(url, domain_sources)
    if inferred_source:
        return inferred_source

    host = _hostname(url)
    return host or "Unknown"
