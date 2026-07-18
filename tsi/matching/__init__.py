"""Motore matching ETS-bando."""

from tsi.matching.engine import (
    match_bando,
    run_scan,
    load_bandi,
    fmt_euro,
    fmt_match_reason,
    parse_date_flex,
    normalise_bando,
    classify_bando,
)
from tsi.matching.patterns import (
    get_pattern_from_tags,
    get_sections_from_tags,
    get_province_filter,
    extract_tags_from_text,
    normalize_comune,
    TAG_PATTERN,
    SECTION_TAG_MAP,
    TEXT_KEYWORDS,
)

__all__ = [
    "match_bando", "run_scan", "load_bandi",
    "fmt_euro", "fmt_match_reason", "parse_date_flex",
    "normalise_bando", "classify_bando",
    "get_pattern_from_tags", "get_sections_from_tags",
    "get_province_filter", "extract_tags_from_text",
    "normalize_comune",
    "TAG_PATTERN", "SECTION_TAG_MAP", "TEXT_KEYWORDS",
]
