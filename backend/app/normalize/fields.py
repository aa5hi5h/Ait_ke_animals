"""Field-aware, safe value normalization (Step 5).

Each extracted value is standardized so that harmless formatting differences
(case, whitespace, date formats, grouped digits, safe abbreviations) collapse
to one comparison key, while anything that would require guessing (OCR glyph
confusions, spelling variants, malformed values) is left untouched and
reported as a warning instead.
"""

from __future__ import annotations

import re
import unicodedata

from app.extract.types import ExtractedField
from app.normalize.types import NormalizedField

# --------------------------------------------------------------- field types
FIELD_TYPES: dict[str, str] = {
    "name": "name",
    "father_name": "name",
    "dob": "date",
    "bill_date": "date",
    "issue_date": "date",
    "id_number": "id_number",
    "pincode": "pincode",
    "gender": "gender",
    "annual_income": "income",
    "address": "address",
    "house_no": "address",
    "locality": "address",
    "city": "address",
    "state": "address",
    "account_number": "account_number",
}
DEFAULT_FIELD_TYPE = "text"


def field_type_of(field_name: str) -> str:
    return FIELD_TYPES.get(field_name, DEFAULT_FIELD_TYPE)


# ------------------------------------------------------------- general rules
def _clean(value: str, transformations: list[str]) -> str:
    """Strip, collapse spaces and normalize Unicode; record each step."""
    text = unicodedata.normalize("NFKC", value)
    if text != value:
        transformations.append("unicode_nfkc")
    stripped = text.strip()
    if stripped != text:
        transformations.append("strip_whitespace")
    collapsed = re.sub(r"\s+", " ", stripped)
    if collapsed != stripped:
        transformations.append("collapse_spaces")
    return collapsed


def _lower(text: str, transformations: list[str]) -> str:
    lowered = text.lower()
    if lowered != text:
        transformations.append("lowercase")
    return lowered


# ---------------------------------------------------------------- name rules
# Only the exact abbreviation forms the synthetic generator produces.
NAME_ABBREVIATIONS = {"mohd": "mohammad", "kr": "kumar"}
_TITLE_PUNCTUATION = re.compile(r"[.,]")


def _normalize_name(value: str) -> tuple[str, str, list[str], list[str]]:
    transformations: list[str] = []
    warnings: list[str] = []
    text = _clean(value, transformations)

    if _TITLE_PUNCTUATION.search(text):
        text = _TITLE_PUNCTUATION.sub("", text)
        transformations.append("remove_title_punctuation")

    tokens: list[str] = []
    for token in text.split(" "):
        lowered = token.lower()
        expanded = NAME_ABBREVIATIONS.get(lowered)
        if expanded is not None:
            transformations.append(f"expand_abbreviation:{lowered}->{expanded}")
            lowered = expanded
        tokens.append(lowered)

    if not tokens:
        warnings.append("name: empty value after cleanup")
        return text, "", transformations, warnings

    normalized_value = " ".join(tokens)
    if normalized_value != text:
        transformations.append("lowercase")
    comparison_key = " ".join(sorted(tokens))   # order-insensitive
    if comparison_key != normalized_value:
        transformations.append("sort_name_tokens")
    return normalized_value, comparison_key, transformations, warnings


# ---------------------------------------------------------------- date rules
_MONTHS = {name: i for i, name in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
_MONTH_PATTERN = "|".join(_MONTHS)

_DATE_NUMERIC = re.compile(
    r"^(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4})$")
_DATE_DAY_MONTH_YEAR = re.compile(
    rf"^(\d{{1,2}})\s*[/.\-\s]\s*({_MONTH_PATTERN})[a-z]*\s*[/.\-\s]\s*(\d{{4}})$",
    re.I)
_DATE_MONTH_NAME = re.compile(
    rf"^({_MONTH_PATTERN})[a-z]*\s+(\d{{1,2}}),?\s+(\d{{4}})$", re.I)


def _iso(day: int, month: int, year: int) -> str | None:
    if not (1 <= month <= 12):
        return None
    max_day = 31 if month in {1, 3, 5, 7, 8, 10, 12} else 30
    if month == 2:
        leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        max_day = 29 if leap else 28
    if not (1 <= day <= max_day):
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def _parse_date(text: str) -> str | None:
    """Parse supported date forms to ISO `YYYY-MM-DD` (or None)."""
    match = _DATE_NUMERIC.match(text)
    if match:
        first, second, year = (int(g) for g in match.groups())
        return (_iso(first, second, year)          # DD/MM/YYYY (generator form)
                or _iso(second, first, year))       # fallback: MM/DD/YYYY
    match = _DATE_DAY_MONTH_YEAR.match(text)
    if match:
        day, month_name, year = match.groups()
        return _iso(int(day), _MONTHS[month_name.lower()], int(year))
    match = _DATE_MONTH_NAME.match(text)
    if match:
        month_name, day, year = match.groups()
        return _iso(int(day), _MONTHS[month_name.lower()], int(year))
    return None


def _normalize_date(value: str) -> tuple[str, str, list[str], list[str]]:
    transformations: list[str] = []
    warnings: list[str] = []
    text = _clean(value, transformations)
    parsed = _parse_date(text)
    if parsed is None:
        warnings.append(f"date: could not parse {text!r}; keeping conservative "
                        f"cleaned value (no guess)")
        return text, text.lower(), transformations, warnings
    transformations.append("parse_date_to_iso")
    return parsed, parsed, transformations, warnings


# ------------------------------------------------------------- id number rule
def _normalize_id_number(value: str) -> tuple[str, str, list[str], list[str]]:
    transformations: list[str] = []
    warnings: list[str] = []
    text = _clean(value, transformations)

    digits = re.sub(r"\D", "", text)
    if digits != text:
        transformations.append("strip_id_punctuation")
    if len(digits) == 12:
        transformations.append("canonical_12_digit_id")
        return digits, digits, transformations, warnings
    warnings.append(f"id_number: expected 12 digits, found {len(digits)}; "
                    f"padding/inventing digits is not allowed")
    key = digits if digits else text.lower()
    return text, key, transformations, warnings


# -------------------------------------------------------------- pincode rule
def _normalize_pincode(value: str) -> tuple[str, str, list[str], list[str]]:
    transformations: list[str] = []
    warnings: list[str] = []
    text = _clean(value, transformations)
    digits = re.sub(r"\D", "", text)
    if len(digits) == 6:
        if digits != text:
            transformations.append("strip_pincode_punctuation")
        return digits, digits, transformations, warnings
    warnings.append(f"pincode: expected 6 digits, found {len(digits)}; "
                    f"keeping cleaned value")
    return text, digits or text.lower(), transformations, warnings


# -------------------------------------------------------------- gender rule
_GENDER_MAP = {
    "male": "male", "m": "male", "man": "male",
    "female": "female", "f": "female", "woman": "female",
    "other": "other", "o": "other",
}


def _normalize_gender(value: str) -> tuple[str, str, list[str], list[str]]:
    transformations: list[str] = []
    warnings: list[str] = []
    text = _clean(value, transformations)
    lowered = _lower(text, transformations)
    mapped = _GENDER_MAP.get(lowered)
    if mapped is None:
        warnings.append(f"gender: unknown value {text!r}; not mapped to a "
                        f"known form")
        return text, lowered, transformations, warnings
    if mapped != text:
        transformations.append("canonicalize_gender")
    return mapped, mapped, transformations, warnings


# ---------------------------------------------------------------- income rule
_CURRENCY = re.compile(r"(?:rs\.?|inr)\s*", re.I)


def _normalize_income(value: str) -> tuple[str, str, list[str], list[str]]:
    transformations: list[str] = []
    warnings: list[str] = []
    text = _clean(value, transformations)

    stripped = _CURRENCY.sub("", text)
    if stripped != text:
        transformations.append("remove_currency_text")
    grouped = stripped.replace(",", "").replace(" ", "")
    if grouped != stripped:
        transformations.append("remove_grouping_separators")

    if grouped.isdigit() and grouped:
        canonical = str(int(grouped))              # numeric integer string
        if canonical != grouped:
            transformations.append("canonicalize_integer")
        return canonical, canonical, transformations, warnings
    warnings.append(f"income: {text!r} is not a plain number; keeping "
                    f"cleaned value (no digits inferred)")
    return text, text.lower(), transformations, warnings


# ------------------------------------------------------------- address rules
# Only unambiguous abbreviations produced by the generator are expanded.
_ADDRESS_ABBREVIATIONS = {"rd": "road", "st": "street", "nr": "near"}
_ADDRESS_ABBREV_RE = re.compile(r"\b(rd|st|nr)\b", re.I)
_ADDRESS_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[./][a-z0-9]+)*")


def _expand_address(text: str, transformations: list[str]) -> str:
    def repl(match: re.Match) -> str:
        word = match.group(1).lower()
        transformations.append(f"expand_abbreviation:{word}"
                              f"->{_ADDRESS_ABBREVIATIONS[word]}")
        return _ADDRESS_ABBREVIATIONS[word]
    return _ADDRESS_ABBREV_RE.sub(repl, text)


def _normalize_address_piece(field_name: str,
                             value: str) -> tuple[str, str, list[str],
                                                  list[str]]:
    transformations: list[str] = []
    warnings: list[str] = []
    text = _clean(value, transformations)
    lowered = _lower(text, transformations)
    expanded = _expand_address(lowered, transformations)

    if field_name == "address":
        # word-order insensitive key that keeps every token and number
        tokens = sorted(_ADDRESS_TOKEN_RE.findall(expanded))
        if not tokens:
            warnings.append("address: empty value after cleanup")
            comparison_key = ""
        else:
            comparison_key = " ".join(tokens)
            if comparison_key != expanded:
                transformations.append("sort_address_tokens")
        return expanded, comparison_key, transformations, warnings

    # house_no / locality / city / state: order is meaningful, keep as-is;
    # numbers and separators stay exactly as extracted
    return expanded, expanded, transformations, warnings


# ------------------------------------------------------- account number rule
def _normalize_account(value: str) -> tuple[str, str, list[str], list[str]]:
    transformations: list[str] = []
    warnings: list[str] = []
    text = _clean(value, transformations)
    compact = re.sub(r"[\s-]", "", text)
    if compact != text:
        transformations.append("remove_formatting_separators")
    if not compact.isdigit():
        warnings.append(f"account_number: {text!r} contains non-digit "
                        f"characters; digits left unchanged")
    lowered = compact.lower()
    if lowered != compact:
        transformations.append("lowercase")
    return compact, lowered, transformations, warnings


# ------------------------------------------------------------ generic text
def _normalize_text(value: str) -> tuple[str, str, list[str], list[str]]:
    transformations: list[str] = []
    warnings: list[str] = []
    text = _clean(value, transformations)
    key = _lower(text, transformations)
    # remove only clearly non-semantic punctuation for comparison
    stripped_key = re.sub(r"[^\w\s/]", "", key)
    if stripped_key != key:
        transformations.append("remove_non_semantic_punctuation")
    comparison_key = re.sub(r"\s+", " ", stripped_key).strip()
    if not comparison_key:
        warnings.append("text: nothing comparable left after cleanup")
        return text, "", transformations, warnings
    return text, comparison_key, transformations, warnings


_NORMALIZERS = {
    "name": _normalize_name,
    "date": _normalize_date,
    "id_number": _normalize_id_number,
    "pincode": _normalize_pincode,
    "gender": _normalize_gender,
    "income": _normalize_income,
    "account_number": _normalize_account,
    "text": _normalize_text,
}


def normalize_value(field_name: str,
                    value: str) -> tuple[str | None, str | None, str,
                                         list[str], list[str]]:
    """Normalize one non-empty value.

    Returns (normalized_value, comparison_key, field_type, transformations,
    warnings). Never guesses: malformed input keeps a conservative cleaned
    string plus a warning.
    """
    field_type = field_type_of(field_name)
    if field_type == "address":
        normalized, key, transformations, warnings = _normalize_address_piece(
            field_name, value)
    else:
        normalized, key, transformations, warnings = _NORMALIZERS[
            field_type](value)
    if normalized == "":
        normalized = None
    if key == "":
        key = None
    return normalized, key, field_type, transformations, warnings


def normalize_field(field_name: str,
                    extracted: ExtractedField) -> NormalizedField:
    """Normalize one extracted field, preserving its raw evidence."""
    raw_value = extracted.value
    field_type = field_type_of(field_name)

    if raw_value is None:
        # missing/ambiguous extraction: keep the status, invent nothing
        if extracted.status == "ambiguous":
            warnings = ["status: ambiguous (no value to normalize; evidence "
                        "retained in extraction)"]
        else:
            warnings = ["status: missing (no value to normalize; nothing "
                        "extracted)"]
        return NormalizedField(
            raw_value=None,
            normalized_value=None,
            comparison_key=None,
            field_type=field_type,
            transformations=[],
            warnings=warnings,
            source_confidence=extracted.confidence,
            source_bbox=extracted.bbox,
        )

    normalized, key, field_type, transformations, warnings = normalize_value(
        field_name, raw_value)
    return NormalizedField(
        raw_value=raw_value,
        normalized_value=normalized,
        comparison_key=key,
        field_type=field_type,
        transformations=transformations,
        warnings=warnings,
        source_confidence=extracted.confidence,
        source_bbox=extracted.bbox,
    )
