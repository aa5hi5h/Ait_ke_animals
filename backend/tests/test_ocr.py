"""Tests for the OCR pipeline (Step 3)."""

import pytest

from app.ocr.engine import rescale_bbox, run_ocr
from app.ocr.preprocess import load_image, preprocess_image
from app.ocr.types import OCRError, OCRResult
from app.synthetic.generate import generate_bundles


@pytest.fixture(scope="module")
def bundle_dir(tmp_path_factory):
    """One freshly generated bundle shared by the OCR tests."""
    out = tmp_path_factory.mktemp("synthetic_data")
    generate_bundles(count=1, seed=11, out_dir=out)
    return out


def test_rescale_bbox_known_values():
    # processed image was upscaled 2x -> divide by 2 to get original coords
    assert rescale_bbox([100, 200, 300, 400], scale=2.0,
                        image_width=620, image_height=874) == [50, 100, 150, 200]
    # scale 1.0 is the identity
    assert rescale_bbox([10, 20, 30, 40], 1.0, 100, 100) == [10, 20, 30, 40]
    # boxes are clamped to the original image bounds
    assert rescale_bbox([-5, -5, 5000, 5000], 1.0, 1240, 1748) == [0, 0, 1240, 1748]
    # rounding must never collapse a box to zero size
    x1, y1, x2, y2 = rescale_bbox([10, 10, 11, 11], scale=10.0,
                                  image_width=100, image_height=100)
    assert x2 > x1 and y2 > y1
    # invalid inputs fail loudly
    with pytest.raises(ValueError):
        rescale_bbox([0, 0, 1, 1], scale=0, image_width=10, image_height=10)


def test_preprocess_is_conservative_and_records_operations(bundle_dir):
    path = bundle_dir / "synthetic" / "bundle_0001" / "id_card.png"
    image = load_image(path)

    result = preprocess_image(image)

    # never crops or resizes a normal-sized page image
    assert result.image.shape[:2] == image.shape[:2]
    assert result.scale == 1.0
    # exact metadata of what was applied
    assert result.operations == [
        "grayscale", "denoise_median_blur", "clahe_contrast", "otsu_threshold"]
    # stays binarized (single channel) for Tesseract
    assert result.image.ndim == 2


def test_missing_image_raises_clear_error(tmp_path):
    with pytest.raises(OCRError, match="Image not found"):
        run_ocr(tmp_path / "does_not_exist.png")


def test_run_ocr_reads_generated_id_card(bundle_dir):
    path = bundle_dir / "synthetic" / "bundle_0001" / "id_card.png"
    assert path.is_file()

    result = run_ocr(path, languages="eng", preprocess=True)

    assert isinstance(result, OCRResult)
    assert result.source_path == str(path)
    assert result.language == "eng"
    assert result.preprocessing_applied          # preprocessing on by default
    assert result.full_text.strip()              # non-empty text
    assert len(result.words) >= 10               # plenty of recognized words

    for word in result.words:
        x1, y1, x2, y2 = word.bbox
        assert word.text.strip()
        assert x2 > x1 and y2 > y1               # positive dimensions

    # OCR is probabilistic: require at least 3 of 5 stable label words,
    # case-insensitive (exact full-text equality is NOT required).
    haystack = result.full_text.lower()
    labels = ("specimen", "name", "date", "gender", "address")
    hits = sum(1 for label in labels if label in haystack)
    assert hits >= 3, f"only {hits} stable label words found in OCR text"


def test_run_ocr_without_preprocess(bundle_dir):
    path = bundle_dir / "synthetic" / "bundle_0001" / "id_card.png"

    result = run_ocr(path, languages="eng", preprocess=False)

    assert result.preprocessing_applied == []
    assert result.full_text.strip()
