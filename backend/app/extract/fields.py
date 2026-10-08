"""Label-driven, layout-aware field extraction from OCR words (Step 4).

The synthetic documents print a visible label in front of every value
(FULL NAME, DATE OF BIRTH, ...), so extraction finds the label on a line and
takes the words after it as the value. Values are preserved exactly as
Tesseract recognized them: no normalization of names, addresses, dates or
abbreviations happens in this layer.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from app.extract.types import ExtractedField
from app.ocr.types import OCRWord

# ------------------------------------------------------------------ fields
COMMON_FIELDS = ["name", "father_name", "dob", "id_number",
                 "house_no", "locality", "city", "state", "pincode", "address"]
TYPE_FIELDS: dict[str, list[str]] = {
    "id_card": ["gender"],
    "address_proof": ["bill_date", "account_number"],
    "income_certificate": ["annual_income", "issue_date"],
    "unknown": [],
}
ADDRESS_FIELDS = ("address", "house_no", "locality", "city", "state", "pincode")


def fields_for(document_type: str) -> list[str]:
    """Fields to attempt for a document type (common + type-specific)."""
    return COMMON_FIELDS + TYPE_FIELDS.get(document_type, [])


# ------------------------------------------------------------------ labels
# (field, visible label) - punctuation variation on the page is tolerated
# because both sides are reduced to alphanumeric characters before matching.
FIELD_LABELS: list[tuple[str, str]] = [
    ("name", "FULL NAME"),
    ("name", "NAME"),
    ("father_name", "FATHER'S NAME"),
    ("dob", "DATE OF BIRTH"),
    ("gender", "GENDER"),
    ("id_number", "ID NUMBER"),
    ("address", "ADDRESS"),
    ("bill_date", "BILL DATE"),
    ("account_number", "ACCOUNT NUMBER"),
    ("annual_income", "ANNUAL INCOME"),
    ("issue_date", "ISSUE DATE"),
]

# The generator's row pitch is 104px while a wrapped address line sits ~60px
# below its first line, so a line this close (and without a label) continues
# the address.
ADDRESS_MAX_LINE_GAP = 90

# Indian states (plus a few union territories) used only as a guardrail to
# locate the state part of an address.
STATES = {
    "ANDHRA PRADESH", "ARUNACHAL PRADESH", "ASSAM", "BIHAR", "CHHATTISGARH",
    "GOA", "GUJARAT", "HARYANA", "HIMACHAL PRADESH", "JHARKHAND", "KARNATAKA",
    "KERALA", "MADHYA PRADESH", "MAHARASHTRA", "MANIPUR", "MEGHALAYA", "MIZORAM",
    "NAGALAND", "ODISHA", "PUNJAB", "RAJASTHAN", "SIKKIM", "TAMIL NADU",
    "TELANGANA", "TRIPURA", "UTTAR PRADESH", "UTTARAKHAND", "WEST BENGAL",
    "DELHI", "CHANDIGARH", "PUDUCHERRY", "JAMMU AND KASHMIR", "LADAKH",
}
_HOUSE_RE = re.compile(r"^(?:h\.?\s*no\.?|house\s+no\.?)\.?\s*\d[\d/.\- ]*$"
                       r"|^\d[\d/.\- ]*$", re.I)
_LOCALITY_RE = re.compile(r"\b(?:road|street|rd|st|near|nr)\b", re.I)
_PINCODE_RE = re.compile(r"^\d{6}$")
_MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
_DATE_NUMERIC = re.compile(r"^\d{1,2}\s*[/.\-]\s*\d{1,2}\s*[/.\-]\s*\d{2,4}$")
_DATE_TEXT = re.compile(
    rf"^\d{{1,2}}\s*[/.\-\s]\s*(?:{_MONTHS})[a-z]*\s*[/.\-\s]\s*\d{{2,4}}$", re.I)
_DATE_TEXT_ALT = re.compile(rf"^(?:{_MONTHS})[a-z]*\s+\d{{1,2}},?\s+\d{{4}}$", re.I)


# ------------------------------------------------------- validation guardrails
def _is_date(value: str) -> bool:
    v = value.strip()
    return bool(_DATE_NUMERIC.match(v) or _DATE_TEXT.match(v)
                or _DATE_TEXT_ALT.match(v))


def _is_id_number(value: str) -> bool:
    v = value.strip()
    return bool(re.fullmatch(r"[\d ]+", v)) and len(v.replace(" ", "")) == 12


def _is_pincode(value: str) -> bool:
    return bool(_PINCODE_RE.fullmatch(value.strip()))


def _is_gender(value: str) -> bool:
    return value.strip().lower() in {"male", "female", "other"}


def _is_income(value: str) -> bool:
    return bool(re.fullmatch(r"(?:rs\.?|inr)?\s*\d[\d,]*(?:\.\d+)?",
                             value.strip(), re.I))


def _is_account(value: str) -> bool:
    return bool(re.fullmatch(r"\d+", value.strip().replace(" ", "")))


FIELD_VALIDATORS = {
    "dob": _is_date,
    "bill_date": _is_date,
    "issue_date": _is_date,
    "id_number": _is_id_number,
    "pincode": _is_pincode,
    "gender": _is_gender,
    "annual_income": _is_income,
    "account_number": _is_account,
}


# ------------------------------------------------------------------ layout
def _alnum(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def union_bbox(words: Sequence[OCRWord]) -> list[int] | None:
    """Smallest box enclosing all given words (original-image pixels)."""
    if not words:
        return None
    return [min(w.bbox[0] for w in words), min(w.bbox[1] for w in words),
            max(w.bbox[2] for w in words), max(w.bbox[3] for w in words)]


def group_words_into_lines(words: Sequence[OCRWord]) -> list[list[OCRWord]]:
    """Group words into visual lines using their y-coordinates."""
    if not words:
        return []
    heights = sorted(w.bbox[3] - w.bbox[1] for w in words)
    median_height = heights[len(heights) // 2] or 1
    tolerance = max(median_height * 0.6, 6.0)

    ordered = sorted(words, key=lambda w: ((w.bbox[1] + w.bbox[3]) / 2, w.bbox[0]))
    lines: list[list[OCRWord]] = []
    current: list[OCRWord] = []
    center_sum = 0.0
    for word in ordered:
        center = (word.bbox[1] + word.bbox[3]) / 2
        if current and abs(center - center_sum / len(current)) > tolerance:
            lines.append(current)
            current, center_sum = [], 0.0
        current.append(word)
        center_sum += center
    if current:
        lines.append(current)

    for line in lines:
        line.sort(key=lambda w: w.bbox[0])
    lines.sort(key=lambda line: min((w.bbox[1] + w.bbox[3]) / 2 for w in line))
    return lines


def _line_center(line: Sequence[OCRWord]) -> float:
    return sum((w.bbox[1] + w.bbox[3]) / 2 for w in line) / len(line)


def match_label(line: Sequence[OCRWord]) -> tuple[str, int] | None:
    """Match a visible label at the start of a line.

    Returns (field, index_of_first_value_word) using the longest label that
    matches; tolerates punctuation/spacing OCR variations. The value may be
    absent (index == len(line)) - callers decide what that means.
    """
    parts = [_alnum(w.text) for w in line]
    best: tuple[int, str, int] | None = None
    for field, label in FIELD_LABELS:
        target = _alnum(label)
        if not target:
            continue
        acc = ""
        for i, part in enumerate(parts):
            acc += part
            if acc == target:
                if best is None or len(target) > best[0]:
                    best = (len(target), field, i + 1)
                break
            if not target.startswith(acc):
                break
    if best is None:
        return None
    return best[1], best[2]


# ------------------------------------------------------------------ builders
def missing_field() -> ExtractedField:
    return ExtractedField(status="missing")


def _trim_leading_junk(words: list[OCRWord]) -> list[OCRWord]:
    """Drop leading tokens with no ASCII alphanumerics (stray OCR artifacts
    such as '_' or '=' that Tesseract sometimes inserts between the label
    column and the value column)."""
    i = 0
    while i < len(words) and not re.search(r"[A-Za-z0-9]", words[i].text):
        i += 1
    return words[i:]


def _field_from(words: Sequence[OCRWord], value: str | None,
                status: str) -> ExtractedField:
    """Build a field whose evidence is exactly the given OCR words."""
    confidences = [w.confidence for w in words]
    return ExtractedField(
        value=value,
        confidence=round(sum(confidences) / len(confidences), 2),
        bbox=union_bbox(words),
        source_words=[w.text for w in words],
        status=status,
    )


# ------------------------------------------------------------------ address
def _join_address_lines(groups: list[list[OCRWord]]) -> str:
    """Join address lines; the renderer drops the separating comma at wrap
    points, so re-insert one unless the line already ends with punctuation."""
    texts = [" ".join(w.text for w in group) for group in groups]
    out = texts[0]
    for text in texts[1:]:
        out += (", " if not re.search(r"[,;:]$", out) else " ") + text
    return out


def _address_part_groups(line_groups: list[list[OCRWord]]) -> list[list[OCRWord]]:
    """Split address words into comma-separated parts, also starting a new
    part at each line break (the wrap dropped separator)."""
    part_groups: list[list[OCRWord]] = []
    for line_words in line_groups:
        current: list[OCRWord] = []
        for word in line_words:
            current.append(word)
            if "," in word.text:
                part_groups.append(current)
                current = []
        if current:
            part_groups.append(current)
    return part_groups


def _split_address_parts(line_groups: list[list[OCRWord]],
                         warnings: list[str]) -> dict[str, ExtractedField]:
    """Identify house_no / locality / city / state / pincode in the address."""
    parts = [(" ".join(w.text for w in g).strip().strip(", "), g)
             for g in _address_part_groups(line_groups)]
    used: set[int] = set()
    out: dict[str, ExtractedField] = {}

    def take(index: int, field: str, status: str = "found") -> None:
        used.add(index)
        out[field] = _field_from(parts[index][1], parts[index][0], status)

    # pincode: the last bare 6-digit part
    pincode = None
    for i, (text, _) in enumerate(parts):
        if _PINCODE_RE.fullmatch(text):
            pincode = i
    if pincode is not None:
        take(pincode, "pincode")

    # house number: first digit-led part
    house = next((i for i, (text, _) in enumerate(parts)
                  if i not in used and _HOUSE_RE.match(text)), None)
    if house is not None:
        take(house, "house_no")

    # state: a known state name (last match wins)
    state = None
    for i, (text, _) in enumerate(parts):
        if i in used:
            continue
        if text.upper() in STATES:
            state = i
    if state is not None:
        take(state, "state")

    # locality: the part carrying a road/street keyword; city is what remains
    remaining = [i for i in range(len(parts)) if i not in used]
    localities = [i for i in remaining if _LOCALITY_RE.search(parts[i][0])]
    if len(localities) == 1:
        take(localities[0], "locality")
        rest = [i for i in remaining if i != localities[0]]
        if len(rest) == 1:
            take(rest[0], "city")
        elif rest:
            words = [w for i in rest for w in parts[i][1]]
            out["city"] = _field_from(words, None, "ambiguous")
            warnings.append(f"address: could not identify city among "
                            f"{len(rest)} remaining parts")
    elif localities:
        words = [w for i in localities for w in parts[i][1]]
        out["locality"] = _field_from(words, None, "ambiguous")
        warnings.append(f"address: {len(localities)} parts look like a locality")
        rest = [i for i in remaining if i not in localities]
        if len(rest) == 1:
            take(rest[0], "city")
        elif rest:
            words = [w for i in rest for w in parts[i][1]]
            out["city"] = _field_from(words, None, "ambiguous")
    elif remaining:
        # no road keyword: locality and city cannot be told apart
        words = [w for i in remaining for w in parts[i][1]]
        out["locality"] = _field_from(words, None, "ambiguous")
        out["city"] = _field_from(words, None, "ambiguous")
        warnings.append("address: could not separate locality from city")

    for field in ("house_no", "locality", "city", "state", "pincode"):
        out.setdefault(field, missing_field())
    return out


def _extract_address(lines: list[list[OCRWord]],
                     labelled: dict[str, tuple[int, int]],
                     warnings: list[str]) -> dict[str, ExtractedField]:
    """Extract ADDRESS plus its parts from the labelled address row(s)."""
    line_idx, start = labelled["address"]
    row_groups: list[list[OCRWord]] = [_trim_leading_junk(list(lines[line_idx][start:]))]
    # attach nearby label-less lines below (wrapped address continuation)
    previous_center = _line_center(lines[line_idx])
    j = line_idx + 1
    while j < len(lines):
        if match_label(lines[j]) is not None:
            break
        center = _line_center(lines[j])
        if center - previous_center > ADDRESS_MAX_LINE_GAP:
            break
        row_groups.append(list(lines[j]))
        previous_center = center
        j += 1

    value_words = [w for group in row_groups for w in group]
    if not value_words:
        return {field: missing_field() for field in ADDRESS_FIELDS}

    out = {
        "address": _field_from(value_words, _join_address_lines(row_groups),
                               "found"),
    }
    out.update(_split_address_parts(row_groups, warnings))
    return out


# ------------------------------------------------------------------ engine
def extract_fields(words: Sequence[OCRWord],
                   document_type: str) -> tuple[dict[str, ExtractedField],
                                                list[str]]:
    """Extract the fields relevant for `document_type` from OCR words.

    Returns (fields in canonical order, warnings).
    """
    warnings: list[str] = []
    lines = group_words_into_lines(words)

    labelled: dict[str, tuple[int, int]] = {}
    for idx, line in enumerate(lines):
        match = match_label(line)
        if match is not None:
            labelled.setdefault(match[0], (idx, match[1]))   # first wins

    found: dict[str, ExtractedField] = {}
    if "address" in labelled:
        found.update(_extract_address(lines, labelled, warnings))

    for field, (line_idx, start) in labelled.items():
        if field in ADDRESS_FIELDS or field not in fields_for(document_type):
            continue
        value_words = _trim_leading_junk(list(lines[line_idx][start:]))
        if not value_words:
            warnings.append(f"{field}: label found but no value words after it")
            continue
        value = " ".join(w.text for w in value_words)
        validator = FIELD_VALIDATORS.get(field)
        if validator is not None and not validator(value):
            found[field] = _field_from(value_words, None, "ambiguous")
            warnings.append(f"{field}: value {value!r} failed validation, "
                            f"marked ambiguous")
            continue
        found[field] = _field_from(value_words, value, "found")

    ordered = {field: found.get(field, missing_field())
               for field in fields_for(document_type)}
    return ordered, warnings
