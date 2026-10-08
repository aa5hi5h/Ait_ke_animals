"""Tests for the field-extraction layer (Step 4)."""

import pytest

from app.extract.engine import detect_document_type, extract_document
from app.extract.fields import extract_fields, group_words_into_lines, union_bbox
from app.extract.types import ExtractionResult
from app.ocr.types import OCRWord, OCRError
from app.synthetic.generate import generate_bundles


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    """One freshly generated bundle shared by the extraction tests."""
    out = tmp_path_factory.mktemp("extract_data")
    generate_bundles(count=1, seed=11, out_dir=out)
    return out


def _word(text, x1, y1, x2, y2, conf=95.0):
    return OCRWord(text=text, confidence=conf, bbox=[x1, y1, x2, y2], page=1)


# ------------------------------------------------------- deterministic units
def test_group_words_into_lines_by_y():
    words = [
        _word("SPECIMEN", 352, 45, 600, 86),
        _word("ADDRESS", 80, 883, 247, 909),
        _word("60/01,", 440, 879, 545, 915),
        _word("Muzaffarpur,", 440, 937, 664, 975),   # wrapped line, ~60px lower
    ]
    lines = group_words_into_lines(words)
    assert [[w.text for w in line] for line in lines] == [
        ["SPECIMEN"],
        ["ADDRESS", "60/01,"],
        ["Muzaffarpur,"],
    ]


def test_union_bbox_encloses_all_words():
    words = [_word("a", 10, 20, 40, 60), _word("b", 30, 5, 80, 40)]
    assert union_bbox(words) == [10, 5, 80, 60]
    assert union_bbox([]) is None


def test_detect_document_type_from_heading():
    assert detect_document_type("SPECIMEN - SYNTHETIC\nIDENTITY DOCUMENT") == "id_card"
    assert detect_document_type("UTILITY BILL") == "address_proof"
    assert detect_document_type("INCOME CERTIFICATE") == "income_certificate"
    assert detect_document_type("no heading here") == "unknown"


def test_extract_fields_from_manual_words():
    """Deterministic end-to-end extraction from hand-supplied OCR words."""
    words = [
        _word("FULL", 80, 363, 150, 388),
        _word("NAME", 179, 363, 260, 388),
        _word("Advik", 440, 359, 540, 389),
        _word("Maharaj", 550, 359, 700, 397),
        _word("GENDER", 82, 672, 200, 697),
        _word("Male", 443, 671, 530, 701),
        _word("ADDRESS", 81, 880, 240, 905),
        _word("60/01,", 441, 879, 545, 915),
        _word("Chahal", 570, 879, 660, 909),
        _word("Road", 715, 879, 780, 909),
        _word("Muzaffarpur,", 443, 937, 664, 975),
        _word("Mizoram,", 690, 937, 800, 973),
        _word("838637", 873, 937, 970, 967),
    ]
    fields, warnings = extract_fields(words, "id_card")

    assert fields["name"].status == "found"
    assert fields["name"].value == "Advik Maharaj"
    assert fields["name"].confidence == 95.0            # mean of source words
    assert fields["name"].bbox == [440, 359, 700, 397]  # union of value words
    assert fields["name"].source_words == ["Advik", "Maharaj"]

    assert fields["gender"].value == "Male"
    assert fields["address"].value == (
        "60/01, Chahal Road, Muzaffarpur, Mizoram, 838637")
    assert fields["house_no"].value == "60/01"
    assert fields["locality"].value == "Chahal Road"
    assert fields["city"].value == "Muzaffarpur"
    assert fields["state"].value == "Mizoram"
    assert fields["pincode"].value == "838637"

    # never invent a value: no label -> missing with null value
    assert fields["dob"].status == "missing"
    assert fields["dob"].value is None
    assert fields["dob"].bbox is None
    assert warnings == []


# ------------------------------------------------------- full pipeline
def test_extract_three_documents(bundle):
    cases = {
        "id_card": ["name", "dob", "id_number", "gender"],
        "address_proof": ["name", "pincode", "bill_date", "account_number"],
        "income_certificate": ["name", "annual_income", "issue_date"],
    }
    for stem, required in cases.items():
        path = bundle / "synthetic" / "bundle_0001" / f"{stem}.png"
        result = extract_document(path)

        assert isinstance(result, ExtractionResult)
        assert result.document_type == stem, (stem, result.warnings)
        assert result.ocr_word_count > 0
        assert result.source_path == str(path)

        name = result.fields["name"]
        assert name.status == "found"
        assert name.value and name.value.strip()

        for field_name in required:
            field = result.fields[field_name]
            assert field.status == "found", (stem, field_name, field, result.warnings)
            assert field.value
            x1, y1, x2, y2 = field.bbox
            assert x2 > x1 and y2 > y1
            assert 0 <= field.confidence <= 100


def test_extract_document_missing_image(tmp_path):
    with pytest.raises(OCRError, match="Image not found"):
        extract_document(tmp_path / "does_not_exist.png")
