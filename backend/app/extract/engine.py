"""Document field extraction engine (Step 4).

Runs the existing OCR engine, detects the document type from its heading,
and extracts label-driven fields with OCR evidence (value, confidence, bbox).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from app.extract.fields import _alnum, extract_fields
from app.extract.types import ExtractionResult
from app.ocr.engine import run_ocr
from app.ocr.types import OCRError

# Reliable heading text printed on each synthetic document type.
HEADINGS = {
    "id_card": "IDENTITY DOCUMENT",
    "address_proof": "UTILITY BILL",
    "income_certificate": "INCOME CERTIFICATE",
}


def detect_document_type(full_text: str) -> str:
    """Detect the document type from its heading; 'unknown' if uncertain."""
    haystack = _alnum(full_text)
    hits = [doc_type for doc_type, heading in HEADINGS.items()
            if _alnum(heading) in haystack]
    return hits[0] if len(hits) == 1 else "unknown"


def extract_from_ocr(ocr_result) -> ExtractionResult:
    """Build an ExtractionResult from an already-computed OCRResult."""
    document_type = detect_document_type(ocr_result.full_text)
    warnings: list[str] = []
    if document_type == "unknown":
        warnings.append("could not confidently detect the document type "
                        "from the heading text")
    fields, field_warnings = extract_fields(ocr_result.words, document_type)
    warnings.extend(field_warnings)
    return ExtractionResult(
        source_path=ocr_result.source_path,
        document_type=document_type,
        fields=fields,
        ocr_word_count=len(ocr_result.words),
        warnings=warnings,
    )


def extract_document(image_path: Path | str,
                     preprocess: bool = True) -> ExtractionResult:
    """OCR one document image and extract its structured fields.

    Raises OCRError with a clear message if the image is missing/unreadable
    or Tesseract cannot run.
    """
    ocr_result = run_ocr(image_path, languages="eng", preprocess=preprocess)
    return extract_from_ocr(ocr_result)


# ------------------------------------------------------------- evaluation
def _eval_clean(text: str) -> str:
    """Whitespace/case cleanup used ONLY for evaluation comparisons."""
    return re.sub(r"\s+", " ", text).strip().lower()


def _evaluate(data_dir: Path, output: Path | None, preprocess: bool) -> int:
    """Compare extraction against ground-truth labels; print a report.

    Writes nothing unless an explicit --output path is supplied.
    """
    synth_dir = data_dir / "synthetic"
    labels_dir = data_dir / "labels"
    images = sorted(synth_dir.glob("bundle_*/*.png"))
    if not images:
        print(f"error: no images found under {synth_dir}", file=sys.stderr)
        return 1

    per_field: dict[str, dict[str, int]] = {}
    mismatches: list[dict] = []
    checked = matched = missing = 0

    for i, image in enumerate(images, 1):
        bundle_id, doc_key = image.parent.name, image.stem
        try:
            label = json.loads(
                (labels_dir / f"{bundle_id}.json").read_text(encoding="utf-8"))
            ground_truth = label["documents"][doc_key]["fields"]
        except (OSError, KeyError, json.JSONDecodeError) as exc:
            print(f"error: cannot read label for {image}: {exc}",
                  file=sys.stderr)
            return 1

        try:
            result = extract_document(image, preprocess=preprocess)
        except OCRError as exc:
            print(f"error: {image}: {exc}", file=sys.stderr)
            return 1

        for field_name, truth in ground_truth.items():
            stats = per_field.setdefault(
                field_name, {"checked": 0, "matched": 0, "missing": 0})
            stats["checked"] += 1
            checked += 1
            ours = result.fields.get(field_name)
            if ours is None or ours.value is None:
                stats["missing"] += 1
                missing += 1
            elif _eval_clean(ours.value) == _eval_clean(truth["value"]):
                stats["matched"] += 1
                matched += 1
            else:
                mismatches.append({
                    "bundle_id": bundle_id, "document": doc_key,
                    "field": field_name, "expected": truth["value"],
                    "extracted": ours.value,
                })
        if i % 20 == 0 or i == len(images):
            print(f"  evaluated {i}/{len(images)} images")

    accuracy = 100.0 * matched / checked if checked else 0.0
    print(f"\n== extraction evaluation: {data_dir} ==")
    print(f"images: {len(images)}")
    print(f"{'field':<18}{'checked':>9}{'matched':>9}{'missing':>9}"
          f"{'accuracy':>11}")
    for field_name in sorted(per_field):
        stats = per_field[field_name]
        acc = (100.0 * stats["matched"] / stats["checked"]
               if stats["checked"] else 0.0)
        print(f"{field_name:<18}{stats['checked']:>9}{stats['matched']:>9}"
              f"{stats['missing']:>9}{acc:>10.1f}%")
    print("-" * 56)
    print(f"{'overall':<18}{checked:>9}{matched:>9}{missing:>9}"
          f"{accuracy:>10.1f}%")
    print(f"total field instances (overall field count): {checked}")
    print(f"missing-field count: {missing}")
    print(f"mismatched values: {checked - matched - missing}")

    if output is not None:
        report = {
            "data_dir": str(data_dir),
            "images": len(images),
            "preprocessing": preprocess,
            "total_fields": checked,
            "matched": matched,
            "missing": missing,
            "mismatched": checked - matched - missing,
            "accuracy_percent": round(accuracy, 2),
            "per_field": {
                name: {
                    **stats,
                    "accuracy_percent": round(
                        100.0 * stats["matched"] / stats["checked"], 2)
                    if stats["checked"] else 0.0,
                }
                for name, stats in sorted(per_field.items())
            },
            "mismatches": mismatches,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
        print(f"report written: {output}")
    return 0


# --------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract structured fields from a document image.")
    parser.add_argument("image", nargs="?", type=Path,
                        help="path to the input image")
    parser.add_argument("--output", "-o", type=Path, default=None,
                        help="output JSON path (default: "
                             "data/extraction_results/<image name>.json)")
    parser.add_argument("--no-preprocess", action="store_true",
                        help="skip image preprocessing before OCR")
    parser.add_argument("--evaluate", type=Path, metavar="DATA_DIR",
                        default=None,
                        help="evaluate extraction against ground-truth labels "
                             "under DATA_DIR instead of a single image")
    args = parser.parse_args(argv)

    if args.evaluate is not None:
        if args.image is not None:
            parser.error("the image argument and --evaluate are mutually "
                         "exclusive")
        return _evaluate(args.evaluate, output=args.output,
                         preprocess=not args.no_preprocess)
    if args.image is None:
        parser.error("an image path is required (or use --evaluate DATA_DIR)")

    try:
        result = extract_document(args.image, preprocess=not args.no_preprocess)
    except OCRError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    output = args.output or (Path("data/extraction_results")
                             / f"{args.image.stem}.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result.model_dump(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    print(f"document_type: {result.document_type}")
    for name, field in result.fields.items():
        if field.status == "found":
            print(f"{name}: {field.value} ({field.confidence:.1f})")
    if result.warnings:
        print(f"warnings: {len(result.warnings)}")
        for warning in result.warnings:
            print(f"  - {warning}")
    print(f"ocr_words: {result.ocr_word_count}")
    print(f"output: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
