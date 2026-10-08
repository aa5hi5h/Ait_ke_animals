"""Unit tests for the normalization layer (Step 5).

All tests build models directly - no dependence on generated project data.
"""

from __future__ import annotations

from app.extract.types import ExtractedField, ExtractionResult
from app.normalize.engine import normalize_extraction
from app.normalize.fields import normalize_field, normalize_value
from app.normalize.types import NormalizationResult, NormalizedField  # noqa: F401


def _extracted(value: str | None, status: str = "found",
               confidence: float = 91.5,
               bbox: list[int] | None = None) -> ExtractedField:
    return ExtractedField(
        value=value,
        confidence=confidence,
        bbox=bbox or [10, 20, 30, 40],
        source_words=[] if value is None else [value],
        status=status,   # type: ignore[arg-type]
    )


def _key(field_name: str, value: str) -> str | None:
    _, key, _, _, _ = normalize_value(field_name, value)
    return key


# ------------------------------------------------------------------- dates
def test_numeric_and_text_month_dates_share_iso_key():
    numeric = normalize_value("dob", "12/03/2001")
    text_month = normalize_value("dob", "12-Mar-2001")
    assert numeric[1] == text_month[1] == "2001-03-12"
    assert numeric[0] == text_month[0] == "2001-03-12"
    assert "parse_date_to_iso" in numeric[3]


def test_date_parse_failure_keeps_cleaned_value_with_warning():
    normalized, key, _, transformations, warnings = normalize_value(
        "dob", "  31/02/1999 ")
    assert normalized == "31/02/1999"        # conservative cleaned string
    assert key == "31/02/1999"
    assert warnings and "could not parse" in warnings[0]
    assert "parse_date_to_iso" not in transformations


# --------------------------------------------------------------- id number
def test_id_number_spacing_is_irrelevant_to_key():
    spaced = normalize_value("id_number", "6184 9593 1034")
    dashed = normalize_value("id_number", "6184-9593-1034")
    assert spaced[1] == dashed[1] == "618495931034"
    assert spaced[0] == dashed[0] == "618495931034"


def test_id_number_with_wrong_digit_count_warns_and_never_pads():
    normalized, key, _, _, warnings = normalize_value("id_number", "12345")
    assert normalized == "12345"
    assert key == "12345"
    assert len(key) != 12
    assert warnings and "12 digits" in warnings[0]


# ------------------------------------------------------------------ names
def test_mohammad_and_mohd_share_name_key():
    assert _key("name", "Mohammad Kumar") == _key("name", "Mohd. Kr.")
    assert _key("name", "Mohammad Kumar") == "kumar mohammad"


def test_reordered_and_case_varied_names_share_key():
    assert _key("name", "Advik Maharaj") == _key("name", "MAHARAJ ADVIK")
    assert _key("name", "Advik Maharaj") == "advik maharaj"


def test_spelling_variants_stay_different():
    assert _key("name", "Ravi Sharma") != _key("name", "Ravi Sarma")
    assert _key("name", "Ravi Singh") != _key("name", "Ravi Sing")


def test_ocr_glyph_confusion_is_not_corrected():
    assert _key("locality", "Iyengar Ganj Street") != _key(
        "locality", "lyengar Ganj Street")


# ---------------------------------------------------------------- address
def test_address_abbreviation_and_word_order_share_key():
    full = "60/01, Chahal Circle Road, Muzaffarpur, Mizoram, 838637"
    reordered = "mizoram 838637 MUZAFFARPUR chahal circle Rd 60/01"
    assert _key("address", full) == _key("address", reordered)


def test_address_key_keeps_numbers_exactly():
    key = _key("address",
               "H.No. 161, Nayar Ganj Street, Hapur, Punjab, 078161")
    assert key is not None
    tokens = key.split()
    assert "161" in tokens and "078161" in tokens
    assert "h.no" in tokens
    assert tokens == sorted(tokens)


def test_house_no_and_pincode_keys_preserve_values():
    assert _key("house_no", "60/01") == "60/01"
    assert _key("pincode", "838637") == "838637"
    assert _key("pincode", "838 637") == "838637"


def test_pincode_malformed_warns():
    normalized, key, _, _, warnings = normalize_value("pincode", "12")
    assert normalized == "12" and key == "12"
    assert warnings and "6 digits" in warnings[0]


# ----------------------------------------------------------------- income
def test_income_currency_and_grouping_removed():
    normalized, key, _, transformations, warnings = normalize_value(
        "annual_income", "Rs. 9,28,000")
    assert normalized == key == "928000"
    assert warnings == []
    assert "remove_currency_text" in transformations


def test_income_non_numeric_never_infers_digits():
    normalized, key, _, _, warnings = normalize_value(
        "annual_income", "Rs. 9,28,00O")     # trailing letter O, not zero
    assert warnings and "no digits inferred" in warnings[0]
    assert key is not None and "928000" not in key
    assert normalized != "928000"


# ------------------------------------------------------------ other values
def test_gender_known_and_unknown_forms():
    assert normalize_value("gender", "Female")[0] == "female"
    assert normalize_value("gender", "F")[0] == "female"
    normalized, key, _, _, warnings = normalize_value("gender", "Mail")
    assert normalized == "Mail" and key == "mail"
    assert warnings and "unknown value" in warnings[0]


def test_account_number_removes_formatting_only():
    normalized, key, _, _, warnings = normalize_value(
        "account_number", "4752 5534-192")
    assert normalized == key == "47525534192"
    assert warnings == []


# ------------------------------------------- raw evidence is never touched
def test_raw_value_confidence_and_bbox_survive_unchanged():
    extracted = _extracted("Advik Maharaj", confidence=94.25,
                           bbox=[10, 20, 30, 40])
    result = normalize_field("name", extracted)
    assert result.raw_value == "Advik Maharaj"
    assert result.source_confidence == 94.25
    assert result.source_bbox == [10, 20, 30, 40]
    assert result.transformations and result.comparison_key == "advik maharaj"


def test_missing_and_ambiguous_fields_stay_empty_with_status():
    missing = normalize_field("dob", _extracted(None, status="missing",
                                                confidence=None, bbox=None))
    ambiguous = normalize_field(
        "city", _extracted(None, status="ambiguous", confidence=40.0))
    for result in (missing, ambiguous):
        assert result.raw_value is None
        assert result.normalized_value is None
        assert result.comparison_key is None
        assert result.warnings and result.warnings[0].startswith("status:")
    assert "missing" in missing.warnings[0]
    assert "ambiguous" in ambiguous.warnings[0]


# ------------------------------------------------------------- whole result
def test_normalize_extraction_preserves_provenance_and_statuses():
    extraction = ExtractionResult(
        source_path="synthetic/bundle_0001/id_card.png",
        document_type="id_card",
        fields={
            "name": _extracted("Advik Maharaj"),
            "dob": _extracted(None, status="missing", confidence=None,
                              bbox=None),
            "city": _extracted(None, status="ambiguous", confidence=30.0),
        },
        ocr_word_count=50,
    )
    result = normalize_extraction(extraction)

    assert isinstance(result, NormalizationResult)
    assert result.source_path == extraction.source_path
    assert result.document_type == "id_card"
    assert set(result.fields) == {"name", "dob", "city"}
    assert result.fields["name"].comparison_key == "advik maharaj"
    assert result.fields["dob"].raw_value is None
    assert result.fields["city"].raw_value is None
    assert any(w.startswith("dob: status: missing") for w in result.warnings)
    assert any(w.startswith("city: status: ambiguous")
               for w in result.warnings)
