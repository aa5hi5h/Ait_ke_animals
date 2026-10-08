"""Document-comparison / contradiction-detection engine (Step 6).

`detect_bundle` runs the existing OCR -> extraction -> normalization pipeline
for every supported document in a bundle folder and compares the normalized
fields across documents. Ground-truth labels are read only inside the
explicit `--evaluate` mode.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.detect.rules import compare_fields, summarize_findings
from app.detect.types import BundleDetectionResult, DetectionError, Finding
from app.extract.engine import extract_document
from app.normalize.engine import normalize_extraction
from app.ocr.types import OCRError

# Names used by the generated demonstration bundles.  Runtime detection does
# not require these names: uploaded files can have any safe PNG filename and
# their type is determined by the extraction layer.
EXPECTED_DEMONSTRATION_DOCUMENTS = ("address_proof", "id_card",
                                    "income_certificate")

DECISION_ORDER = ("conflict", "harmless_variant", "review",
                  "insufficient_evidence")


def detect_bundle(bundle_path: Path | str,
                  preprocess: bool = True) -> BundleDetectionResult:
    """Compare all supported documents inside one bundle folder.

    Raises DetectionError when the folder is missing or holds fewer than two
    readable documents; unreadable individual documents become warnings.
    """
    bundle = Path(bundle_path)
    if not bundle.is_dir():
        raise DetectionError(f"bundle folder not found: {bundle}")

    warnings: list[str] = []
    # The API intentionally preserves client filenames, so never depend on
    # fixture-specific names here.  Sorting makes output reproducible.
    images = sorted(bundle.glob("*.png"), key=lambda path: path.name.lower())

    normalizations = []
    for image in images:
        try:
            extraction = extract_document(image, preprocess=preprocess)
        except OCRError as exc:
            warnings.append(f"{image.name}: unreadable - {exc}")
            continue
        normalizations.append(normalize_extraction(extraction))

    if len(normalizations) < 2:
        raise DetectionError(
            f"bundle {bundle} needs at least two readable documents, got "
            f"{len(normalizations)}")

    findings = compare_fields(normalizations)
    return BundleDetectionResult(
        bundle_path=str(bundle),
        documents_processed=len(normalizations),
        findings=findings,
        summary=summarize_findings(findings),
        warnings=warnings,
    )


# ----------------------------------------------------------------- reporting
def format_report(result: BundleDetectionResult) -> str:
    """Concise human-readable report grouped by decision."""
    lines = [f"bundle: {result.bundle_path}",
             f"documents processed: {result.documents_processed}"]
    if result.warnings:
        lines.append(f"warnings: {len(result.warnings)}")
        lines.extend(f"  - {w}" for w in result.warnings)

    lines.append("")
    lines.append("findings by decision:")
    if not result.findings:
        lines.append("  (none - all compared fields agree)")
    for decision in DECISION_ORDER:
        group = [f for f in result.findings if f.decision == decision]
        if not group:
            continue
        lines.append(f"  [{decision}] {len(group)}")
        for finding in group:
            sim = ("" if finding.similarity is None
                   else f" (similarity {finding.similarity})")
            lines.append(f"    - {finding.field} ({finding.severity}){sim}")
            lines.append(f"      reason: {finding.reason}")
            for ev in finding.evidence:
                conf = ("?" if ev.source_confidence is None
                        else f"{ev.source_confidence:g}")
                value = ev.raw_value if ev.raw_value is not None else "<missing>"
                lines.append(f"      {ev.document_type}: {value!r} "
                             f"(confidence {conf})")
            lines.append(f"      action: {finding.recommended_action}")

    lines.append("")
    lines.append("summary:")
    for key in ("conflict_count", "harmless_variant_count", "review_count",
                "insufficient_evidence_count"):
        lines.append(f"  {key}: {result.summary.get(key)}")
    lines.append(f"  highest_severity: {result.summary.get('highest_severity')}")
    return "\n".join(lines)


# -------------------------------------------------------------- evaluation
def _evaluate(data_dir: Path, output: Path | None,
              preprocess: bool) -> int:
    """Evaluate detections against label files (labels allowed HERE only)."""
    synth_dir = data_dir / "synthetic"
    labels_dir = data_dir / "labels"
    bundles = sorted(p for p in synth_dir.glob("bundle_*") if p.is_dir())
    if not bundles:
        print(f"error: no bundles found under {synth_dir}", file=sys.stderr)
        return 1

    tp = fp = fn = 0
    harmless_ok = harmless_bad = 0
    review_count = 0
    mismatch_lines: list[str] = []
    errors: list[str] = []

    for index, bundle in enumerate(bundles, 1):
        bundle_id = bundle.name
        try:
            label = json.loads(
                (labels_dir / f"{bundle_id}.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{bundle_id}: cannot read label ({exc})")
            continue
        scenario = label.get("scenario", "?")
        injected = label.get("injected", [])

        try:
            result = detect_bundle(bundle, preprocess=preprocess)
        except DetectionError as exc:
            errors.append(f"{bundle_id}: {exc}")
            continue
        review_count += result.summary.get("review_count", 0)

        conflict_fields = {f.field for f in result.findings
                           if f.decision == "conflict"}
        findings_by_field: dict[str, list[Finding]] = {}
        for finding in result.findings:
            findings_by_field.setdefault(finding.field, []).append(finding)

        for entry in injected:
            field = entry["field"]
            field_findings = findings_by_field.get(field, [])
            decisions = [f.decision for f in field_findings]
            if entry["is_conflict"]:
                if field in conflict_fields:
                    tp += 1
                else:
                    fn += 1
                    got = ", ".join(decisions) or "no finding"
                    mismatch_lines.append(
                        f"{bundle_id} ({scenario}): expected conflict on "
                        f"'{field}', got {got}")
            else:
                if not field_findings or all(
                        f.decision == "harmless_variant"
                        for f in field_findings):
                    harmless_ok += 1
                else:
                    harmless_bad += 1
                    got = ", ".join(decisions)
                    mismatch_lines.append(
                        f"{bundle_id} ({scenario}): expected harmless variant "
                        f"on '{field}', got {got}")

        for finding in result.findings:
            entry = next((e for e in injected
                          if e["field"] == finding.field), None)
            if finding.decision == "conflict":
                if entry is None or not entry["is_conflict"]:
                    fp += 1
                    expected = ("no finding expected"
                                if entry is None else "expected harmless")
                    mismatch_lines.append(
                        f"{bundle_id} ({scenario}): false positive conflict "
                        f"on '{finding.field}' ({expected})")
            elif entry is None:
                mismatch_lines.append(
                    f"{bundle_id} ({scenario}): unexpected "
                    f"{finding.decision} finding on unlabeled field "
                    f"'{finding.field}'")

        if index % 5 == 0 or index == len(bundles):
            print(f"  evaluated {index}/{len(bundles)} bundles")

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if precision + recall else 0.0)
    harmless_total = harmless_ok + harmless_bad
    harmless_acc = harmless_ok / harmless_total if harmless_total else 0.0

    print(f"\n== detection evaluation: {data_dir} ==")
    print(f"bundles evaluated: {len(bundles) - len(errors)}/{len(bundles)}")
    print(f"real conflicts: TP={tp} FP={fp} FN={fn}")
    print(f"precision: {precision:.4f}")
    print(f"recall:    {recall:.4f}")
    print(f"F1:        {f1:.4f}")
    print(f"harmless-variant classification accuracy: "
          f"{harmless_ok}/{harmless_total} = {harmless_acc:.4f}")
    print(f"false positives: {fp}")
    print(f"false negatives: {fn}")
    print(f"review findings: {review_count}")
    if errors:
        print("errors:")
        for line in errors:
            print(f"  - {line}")
    if mismatch_lines:
        print("mismatches:")
        for line in mismatch_lines:
            print(f"  - {line}")
    else:
        print("mismatches: none")

    if output is not None:
        report = {
            "data_dir": str(data_dir),
            "bundles_evaluated": len(bundles) - len(errors),
            "bundles_total": len(bundles),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "harmless_variant_accuracy": round(harmless_acc, 4),
            "harmless_variant_total": harmless_total,
            "review_findings": review_count,
            "mismatches": mismatch_lines,
            "errors": errors,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2)
                          + "\n", encoding="utf-8")
        print(f"report written: {output}")
    return 0


# --------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare the documents of a bundle and detect "
                    "contradictions.")
    parser.add_argument("bundle", nargs="?", type=Path,
                        help="folder containing the bundle's document PNGs")
    parser.add_argument("--output", "-o", type=Path, default=None,
                        help="output JSON path (default: "
                             "data/detection_results/<bundle name>.json)")
    parser.add_argument("--no-preprocess", action="store_true",
                        help="skip image preprocessing before OCR")
    parser.add_argument("--evaluate", type=Path, metavar="DATA_DIR",
                        default=None,
                        help="evaluate all bundles under DATA_DIR against "
                             "their label files (labels used only here)")
    args = parser.parse_args(argv)

    if args.evaluate is not None:
        if args.bundle is not None:
            parser.error("the bundle argument and --evaluate are mutually "
                         "exclusive")
        return _evaluate(args.evaluate, output=args.output,
                         preprocess=not args.no_preprocess)
    if args.bundle is None:
        parser.error("a bundle folder is required (or use --evaluate "
                     "DATA_DIR)")

    try:
        result = detect_bundle(args.bundle,
                               preprocess=not args.no_preprocess)
    except DetectionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    output = args.output or (Path("data/detection_results")
                             / f"{args.bundle.name}.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result.model_dump(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    print(format_report(result))
    print(f"output: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
