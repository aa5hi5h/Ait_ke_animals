"""OCR engine: image -> recognized text + word-level boxes (Step 3).

Uses Tesseract via pytesseract. All returned boxes are in the original
input image's pixel coordinates, even when preprocessing upscaled the image.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Sequence
from pathlib import Path

import pytesseract
from pytesseract import Output

from app.ocr.preprocess import load_image, preprocess_image
from app.ocr.types import OCRResult, OCRWord, OCRError

# Tesseract engine/page-segmentation mode - tune here later if needed.
TESSERACT_CONFIG = "--oem 3 --psm 6"


def _round_half_up(value: float) -> int:
    return int(math.floor(value + 0.5))


def rescale_bbox(bbox: Sequence[float], scale: float,
                 image_width: int, image_height: int) -> list[int]:
    """Map a bbox from processed-image coordinates to original-image pixels.

    `scale` is processed_size / original_size (1.0 when nothing was upscaled).
    Guarantees a box inside the image with positive width and height.
    """
    if scale <= 0:
        raise ValueError(f"scale must be positive, got {scale!r}")
    if image_width < 1 or image_height < 1:
        raise ValueError(f"image dimensions must be positive, "
                         f"got {image_width}x{image_height}")

    x1, y1, x2, y2 = (_round_half_up(float(v) / scale) for v in bbox)
    x1 = min(max(x1, 0), image_width - 1)
    y1 = min(max(y1, 0), image_height - 1)
    x2 = min(max(x2, 0), image_width)
    y2 = min(max(y2, 0), image_height)
    if x2 <= x1:                      # rounding collapsed the box
        x2 = x1 + 1
    if y2 <= y1:
        y2 = y1 + 1
    return [x1, y1, x2, y2]


def run_ocr(image_path: Path | str, languages: str = "eng",
            preprocess: bool = True) -> OCRResult:
    """OCR one image and return recognized words with original-image boxes."""
    path = Path(image_path)
    image = load_image(path)                 # clear error if missing/corrupt
    height, width = image.shape[:2]

    if preprocess:
        processed = preprocess_image(image)
        working, operations, scale = (processed.image, processed.operations,
                                      processed.scale)
    else:
        working, operations, scale = image, [], 1.0

    try:
        data = pytesseract.image_to_data(
            working, lang=languages, config=TESSERACT_CONFIG,
            output_type=Output.DICT)
    except pytesseract.TesseractNotFoundError as exc:
        raise OCRError(
            "Tesseract executable not found. Install Tesseract OCR and make "
            "sure 'tesseract' is on your PATH (see /health/ocr).") from exc
    except pytesseract.TesseractError as exc:
        raise OCRError(
            f"Tesseract failed for {path} (languages={languages!r}): {exc}"
        ) from exc

    words: list[OCRWord] = []
    lines: dict[tuple, list[str]] = {}       # preserves Tesseract reading order
    for i, raw in enumerate(data["text"]):
        text = (raw or "").strip()
        if not text:                          # ignore empty entries
            continue
        confidence = float(data["conf"][i])
        if confidence < 0:                    # Tesseract marks non-words with -1
            continue
        bbox = rescale_bbox(
            [data["left"][i], data["top"][i],
             data["left"][i] + data["width"][i],
             data["top"][i] + data["height"][i]],
            scale, width, height,
        )
        words.append(OCRWord(text=text, confidence=confidence,
                             bbox=bbox, page=1))
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(text)

    full_text = "\n".join(" ".join(group) for group in lines.values())

    return OCRResult(
        source_path=str(path),
        full_text=full_text,
        words=words,
        language=languages,
        preprocessing_applied=operations,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Tesseract OCR on a document image.")
    parser.add_argument("image", type=Path, help="path to the input image")
    parser.add_argument("--output", "-o", type=Path, default=None,
                        help="output JSON path "
                             "(default: data/ocr_results/<image name>.json)")
    parser.add_argument("--lang", default="eng",
                        help="Tesseract language(s), e.g. 'eng' or 'eng+hin' "
                             "(default: eng)")
    parser.add_argument("--no-preprocess", action="store_true",
                        help="skip preprocessing and OCR the raw image")
    args = parser.parse_args(argv)

    try:
        result = run_ocr(args.image, languages=args.lang,
                         preprocess=not args.no_preprocess)
    except OCRError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    output = args.output or Path("data/ocr_results") / f"{args.image.stem}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result.model_dump(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    print(f"words: {len(result.words)}")
    print(f"output: {output}")
    print(f"preprocessing: {result.preprocessing_applied or 'none'}")
    print("text (first 300 chars):")
    print(result.full_text[:300])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
