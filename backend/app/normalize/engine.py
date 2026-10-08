"""Normalization engine: extraction result -> normalized fields (Step 5).

Accepts the existing ExtractionResult directly and produces a
NormalizationResult. Independent from synthetic-label files; it never reads
ground truth at runtime.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.extract.engine import extract_document
from app.extract.types import ExtractionResult
from app.normalize.fields import normalize_field
from app.normalize.types import NormalizationResult
from app.ocr.types import OCRError


def normalize_extraction(
        extraction_result: ExtractionResult) -> NormalizationResult:
    """Normalize every extracted field of one document.

    Missing/ambiguous fields stay missing/ambiguous (no value invented), and
    raw value, confidence and bbox are always preserved on the result.
    """
    fields = {}
    warnings: list[str] = []
    for field_name, extracted in extraction_result.fields.items():
        normalized = normalize_field(field_name, extracted)
        fields[field_name] = normalized
        warnings.extend(f"{field_name}: {w}" for w in normalized.warnings)
    return NormalizationResult(
        source_path=extraction_result.source_path,
        document_type=extraction_result.document_type,
        fields=fields,
        warnings=warnings,
    )


# --------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract structured fields from a document image and "
                    "normalize them for later comparison.")
    parser.add_argument("image", type=Path, help="path to the input image")
    parser.add_argument("--output", "-o", type=Path, default=None,
                        help="output JSON path (default: "
                             "data/normalization_results/<image name>.json)")
    parser.add_argument("--no-preprocess", action="store_true",
                        help="skip image preprocessing before OCR")
    args = parser.parse_args(argv)

    try:
        extraction = extract_document(
            args.image, preprocess=not args.no_preprocess)
    except OCRError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    result = normalize_extraction(extraction)

    output = args.output or (Path("data/normalization_results")
                             / f"{args.image.stem}.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result.model_dump(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    print(f"document_type: {result.document_type}")
    for name, field in result.fields.items():
        if field.raw_value is None:
            continue
        print(f"{name}: {field.raw_value!r} -> "
              f"{field.normalized_value!r} (key: {field.comparison_key!r})")
        if field.transformations:
            print(f"    transformations: {', '.join(field.transformations)}")
        if field.warnings:
            print(f"    warnings: {'; '.join(field.warnings)}")
    if result.warnings:
        print(f"warnings: {len(result.warnings)}")
    print(f"output: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
