"""Unit + integration tests for the detection layer (Step 6).

Unit tests build NormalizationResult models directly - no dependence on
project-generated data or labels. The single integration test generates a
fresh bundle in a temporary folder.
"""

from __future__ import annotations

from app.detect.engine import detect_bundle
from app.detect.rules import compare_fields, summarize_findings
from app.detect.types import BundleDetectionResult, DetectionError
from app.normalize.types import NormalizationResult, NormalizedField
from app.synthetic.generate import generate_bundles

DECISIONS = {"conflict", "harmless_variant", "review", "insufficient_evidence"}


def nf(raw: str | None, key: str | None, *, conf: float | None = 95.0,
       bbox: tuple[int, int, int, int] | None = (10, 20, 30, 40),
       warnings: list[str] | None = None,
       field_type: str = "text") -> NormalizedField:
    return NormalizedField(
        raw_value=raw,
        normalized_value=raw if key is None else key,
        comparison_key=key,
        field_type=field_type,
        transformations=[],
        warnings=list(warnings or []),
        source_confidence=conf,
        source_bbox=list(bbox) if bbox is not None else None,
    )


def doc(doc_type: str, fields: dict[str, NormalizedField],
        path: str | None = None) -> NormalizationResult:
    return NormalizationResult(
        source_path=path or f"data/synthetic/bundle_test/{doc_type}.png",
        document_type=doc_type,
        fields=fields,
        warnings=[],
    )


def findings_for(field: str, results: list[NormalizationResult]):
    return [f for f in compare_fields(results) if f.field == field]


# ------------------------------------------------------------ exact values
def test_same_id_with_formatting_differences_is_not_a_conflict():
    results = [
        doc("id_card", {"id_number": nf("6184 9593 1034", "618495931034")}),
        doc("income_certificate",
            {"id_number": nf("6184-9593-1034", "618495931034")}),
    ]
    assert findings_for("id_number", results) == []
    assert compare_fields(results) == []


def test_differing_valid_ids_are_a_high_conflict():
    results = [
        doc("id_card", {"id_number": nf("6184 9593 1034", "618495931034",
                                        conf=96.0,
                                        bbox=(440, 775, 744, 805))}),
        doc("income_certificate",
            {"id_number": nf("6184 9593 1099", "618495931099", conf=94.0)}),
    ]
    [finding] = findings_for("id_number", results)
    assert finding.decision == "conflict"
    assert finding.severity == "HIGH"
    assert finding.similarity is None
    assert [e.raw_value for e in finding.evidence] == ["6184 9593 1034",
                                                       "6184 9593 1099"]
    assert finding.evidence[0].source_confidence == 96.0
    assert finding.evidence[0].source_bbox == [440, 775, 744, 805]
    assert finding.evidence[0].source_path.endswith("id_card.png")


def test_date_format_difference_normalizing_equally_is_not_a_conflict():
    results = [
        doc("id_card", {"dob": nf("12/03/2001", "2001-03-12")}),
        doc("income_certificate", {"dob": nf("12-Mar-2001", "2001-03-12")}),
    ]
    assert findings_for("dob", results) == []


def test_differing_valid_dobs_are_a_high_conflict():
    results = [
        doc("id_card", {"dob": nf("29/09/1967", "1967-09-29")}),
        doc("income_certificate", {"dob": nf("12/03/2001", "2001-03-12")}),
    ]
    [finding] = findings_for("dob", results)
    assert finding.decision == "conflict"
    assert finding.severity == "HIGH"


def test_equal_pincodes_produce_no_finding():
    results = [
        doc("id_card", {"pincode": nf("838637", "838637")}),
        doc("address_proof", {"pincode": nf("838637", "838637")}),
    ]
    assert findings_for("pincode", results) == []


# ------------------------------------------------------------------ names
def test_sharma_and_sarma_are_a_harmless_variant():
    results = [
        doc("id_card", {"name": nf("Ravi Sharma", "ravi sharma")}),
        doc("income_certificate", {"name": nf("Ravi Sarma", "ravi sarma")}),
    ]
    [finding] = findings_for("name", results)
    assert finding.decision == "harmless_variant"
    assert finding.severity == "NONE"
    assert finding.similarity is not None and finding.similarity >= 88


def test_clearly_unrelated_names_are_a_medium_conflict():
    results = [
        doc("id_card", {"name": nf("Aarav Sharma", "aarav sharma")}),
        doc("income_certificate", {"name": nf("Zoya Khan", "khan zoya")}),
    ]
    [finding] = findings_for("name", results)
    assert finding.decision == "conflict"
    assert finding.severity == "MEDIUM"
    assert finding.similarity is not None and finding.similarity < 70


def test_reordered_name_tokens_produce_no_finding():
    results = [
        doc("id_card", {"name": nf("Advik Maharaj", "advik maharaj")}),
        doc("income_certificate",
            {"name": nf("MAHARAJ ADVIK", "advik maharaj")}),
    ]
    assert findings_for("name", results) == []


def test_poor_confidence_name_prefers_review_over_conflict():
    results = [
        doc("id_card", {"name": nf("Ravi Sharma", "ravi sharma", conf=95.0)}),
        doc("income_certificate",
            {"name": nf("Ravi Mehta", "ravi mehta", conf=50.0)}),
    ]
    [finding] = findings_for("name", results)
    assert finding.decision == "review"
    assert finding.severity == "LOW"


# --------------------------------------------------------------- address
def test_reordered_and_abbreviated_address_is_never_a_conflict():
    results = [
        doc("id_card", {
            "city": nf("Muzaffarpur", "muzaffarpur"),
            "pincode": nf("838637", "838637"),
            "address": nf("60/01, Chahal Circle Road, Muzaffarpur, Mizoram, "
                          "838637",
                          "60/01 838637 chahal circle road mizoram "
                          "muzaffarpur"),
        }),
        doc("income_certificate", {
            "city": nf("Muzaffarpur", "muzaffarpur"),
            "pincode": nf("838637", "838637"),
            "address": nf("Chahal Circle Rd, 60/01 Muzaffarpur, Mizoram, "
                          "838637",
                          "60/01 838637 chahal circle road mizoram "
                          "muzaffarpur"),
        }),
    ]
    assert findings_for("address", results) == []


def test_address_with_small_difference_is_harmless_not_conflict():
    results = [
        doc("id_card", {
            "city": nf("Muzaffarpur", "muzaffarpur"),
            "pincode": nf("838637", "838637"),
            "address": nf("60/01, Chahal Circle Road, Mizoram, 838637",
                          "60/01 838637 chahal circle road mizoram"),
        }),
        doc("income_certificate", {
            "city": nf("Muzaffarpur", "muzaffarpur"),
            "pincode": nf("838637", "838637"),
            "address": nf("60/01, Chahal Circle Road, Muzaffarpur, Mizoram, "
                          "838637",
                          "60/01 838637 chahal circle road mizoram "
                          "muzaffarpur"),
        }),
    ]
    [finding] = findings_for("address", results)
    assert finding.decision in {"harmless_variant", "review"}
    assert finding.decision != "conflict"
    assert finding.severity in {"NONE", "LOW"}


def test_differing_pincodes_yield_one_pincode_conflict_no_address_duplicate():
    results = [
        doc("id_card", {
            "city": nf("Muzaffarpur", "muzaffarpur"),
            "pincode": nf("838637", "838637"),
            "address": nf("60/01, Chahal Circle Road, Muzaffarpur, Mizoram, "
                          "838637",
                          "60/01 838637 chahal circle road mizoram "
                          "muzaffarpur"),
        }),
        doc("address_proof", {
            "city": nf("Muzaffarpur", "muzaffarpur"),
            "pincode": nf("838637", "838637"),
            "address": nf("60/01, Chahal Circle Road, Muzaffarpur, Mizoram, "
                          "838637",
                          "60/01 838637 chahal circle road mizoram "
                          "muzaffarpur"),
        }),
        doc("income_certificate", {
            "city": nf("Muzaffarpur", "muzaffarpur"),
            "pincode": nf("999999", "999999"),
            "address": nf("60/01, Chahal Circle Road, Muzaffarpur, Mizoram, "
                          "999999",
                          "60/01 999999 chahal circle road mizoram "
                          "muzaffarpur"),
        }),
    ]
    findings = compare_fields(results)
    conflicts = [f for f in findings if f.decision == "conflict"]
    assert [f.field for f in conflicts] == ["pincode"]
    assert conflicts[0].severity == "MEDIUM"
    assert findings_for("address", results) == []


# ------------------------------------------------- missing / malformed data
def test_missing_values_never_produce_a_false_conflict():
    results = [
        doc("id_card", {"dob": nf("29/09/1967", "1967-09-29")}),
        doc("income_certificate", {"dob": nf("29/09/1967", "1967-09-29")}),
        doc("address_proof", {"dob": nf(None, None, conf=None, bbox=None,
                                        warnings=["status: missing "
                                                  "(no value to normalize; "
                                                  "nothing extracted)"])}),
    ]
    assert findings_for("dob", results) == []


def test_only_one_usable_value_is_insufficient_evidence():
    results = [
        doc("id_card", {"dob": nf("29/09/1967", "1967-09-29")}),
        doc("income_certificate",
            {"dob": nf("not a date", "not a date",
                       warnings=["date: could not parse 'not a date'; "
                                 "keeping conservative cleaned value (no "
                                 "guess)"])}),
    ]
    [finding] = findings_for("dob", results)
    assert finding.decision == "insufficient_evidence"
    assert finding.severity == "NONE"
    assert finding.evidence[1].raw_value == "not a date"
    assert finding.evidence[1].normalization_warnings


def test_no_usable_values_is_insufficient_evidence_not_conflict():
    results = [
        doc("id_card", {"gender": nf("Unknown", "unknown",
                                     warnings=["gender: unknown value "
                                               "'Unknown'; not mapped to a "
                                               "known form"])}),
        doc("address_proof", {"gender": nf(None, None, conf=None, bbox=None,
                                           warnings=["status: missing"])}),
    ]
    [finding] = findings_for("gender", results)
    assert finding.decision == "insufficient_evidence"
    assert finding.severity == "NONE"


def test_summary_counts_and_highest_severity():
    results = [
        doc("id_card", {"dob": nf("29/09/1967", "1967-09-29"),
                        "name": nf("Ravi Sharma", "ravi sharma"),
                        "pincode": nf("838637", "838637")}),
        doc("income_certificate", {"dob": nf("12/03/2001", "2001-03-12"),
                                   "name": nf("Ravi Sarma", "ravi sarma"),
                                   "pincode": nf("111111", "111111")}),
    ]
    findings = compare_fields(results)
    summary = summarize_findings(findings)
    assert summary["conflict_count"] == 2            # dob + pincode
    assert summary["harmless_variant_count"] == 1    # name
    assert summary["review_count"] == 0
    assert summary["insufficient_evidence_count"] == 0
    assert summary["highest_severity"] == "HIGH"


# --------------------------------------------------------------- integration
def test_detect_bundle_on_a_fresh_generated_bundle(tmp_path):
    generate_bundles(count=1, seed=11, out_dir=tmp_path)
    bundle = tmp_path / "synthetic" / "bundle_0001"

    result = detect_bundle(bundle)

    assert isinstance(result, BundleDetectionResult)
    assert result.bundle_path == str(bundle)
    assert result.documents_processed == 3
    assert set(result.summary) == {"conflict_count", "harmless_variant_count",
                                   "review_count",
                                   "insufficient_evidence_count",
                                   "highest_severity"}
    assert (sum(result.summary[k] for k in
                ("conflict_count", "harmless_variant_count", "review_count",
                 "insufficient_evidence_count"))
            == len(result.findings))
    assert result.summary["highest_severity"] in {"HIGH", "MEDIUM", "LOW",
                                                  "NONE"}
    for finding in result.findings:
        assert finding.decision in DECISIONS
        assert finding.evidence
        for evidence in finding.evidence:
            assert evidence.source_path.endswith(".png")
            assert evidence.document_type in {"id_card", "address_proof",
                                              "income_certificate"}
            if evidence.raw_value is not None:
                assert evidence.source_bbox is not None
                assert evidence.source_confidence is not None


def test_detect_bundle_requires_two_readable_documents(tmp_path):
    (tmp_path / "empty_bundle").mkdir()
    try:
        detect_bundle(tmp_path / "empty_bundle")
    except DetectionError as exc:
        assert "at least two readable documents" in str(exc)
    else:
        raise AssertionError("DetectionError was not raised")
