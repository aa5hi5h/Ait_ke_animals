"""Comparison rules for normalized fields (Step 6).

Given every document's NormalizationResult, decide per field whether the
documents disagree (conflict), agree with only harmless formatting or
spelling differences (harmless_variant), need a human (review), or cannot be
decided at all (insufficient_evidence).

Ground-truth label files are never read here - this module only sees
normalized extraction output.
"""

from __future__ import annotations

import re

from rapidfuzz import fuzz

from app.detect.types import (Finding, SEVERITY_ORDER, FieldEvidence,
                              Severity)
from app.normalize.types import NormalizationResult, NormalizedField

# Fields that are compared across documents, in report order. house_no,
# locality and state are deliberately not compared standalone: their only
# meaningful differences are already carried by the generic `address` field,
# so comparing them would duplicate findings.
COMPARED_FIELDS = ["name", "father_name", "dob", "id_number", "gender",
                   "city", "pincode", "annual_income", "account_number",
                   "address"]

NAME_FIELDS = {"name", "father_name"}

CONFLICT_SEVERITY: dict[str, Severity] = {
    "dob": "HIGH",
    "id_number": "HIGH",
    "name": "MEDIUM",
    "father_name": "MEDIUM",
    "pincode": "MEDIUM",
    "city": "MEDIUM",
    "gender": "MEDIUM",
    "account_number": "MEDIUM",
    "annual_income": "LOW",
    "address": "LOW",
}

RECOMMENDED_ACTION = {
    ("conflict", "HIGH"):
        "Escalate for manual verification before these documents are matched.",
    ("conflict", "MEDIUM"):
        "Review the differing values with the issuing source before matching.",
    ("conflict", "LOW"):
        "Confirm the difference manually if it matters for this record.",
    ("harmless_variant", "NONE"):
        "No action needed; treat the values as equivalent.",
    ("review", "LOW"):
        "Manual review recommended; the evidence is not strong enough for an "
        "automatic decision.",
    ("insufficient_evidence", "NONE"):
        "Inspect the source image or re-run OCR; there is too little usable "
        "evidence to compare.",
}

LOW_CONFIDENCE = 70.0
NAME_HARMLESS_MIN = 88.0      # >= 88  -> harmless spelling/variant
NAME_REVIEW_MIN = 70.0        # 70-88  -> review;  < 70 -> conflict
ADDRESS_HARMLESS_MIN = 85.0

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_GENDERS = {"male", "female", "other"}


# ----------------------------------------------------------------- helpers
def similarity(a: str, b: str) -> float:
    """Token-based similarity between two comparison keys (0-100).

    Uses rapidfuzz' partial token-sort ratio so that harmless token-level
    differences (initials like `A.` vs `Aarush`, spelling variants like
    `Sharma` vs `Sarma`) score high while unrelated names stay far below the
    review threshold.
    """
    return round(float(fuzz.partial_token_sort_ratio(a, b)), 1)


def is_usable(field: str, normalized: NormalizedField) -> bool:
    """True when the value is well-formed enough to decide from."""
    key = normalized.comparison_key
    if not key:
        return False
    if field in ("dob", "bill_date", "issue_date"):
        return bool(_ISO_DATE_RE.match(key))
    if field == "id_number":
        return key.isdigit() and len(key) == 12
    if field == "pincode":
        return key.isdigit() and len(key) == 6
    if field == "gender":
        return key in _GENDERS
    if field in ("annual_income", "account_number"):
        return key.isdigit()
    return True


def _has_poor_evidence(entries: list[tuple[NormalizationResult,
                                           NormalizedField]]) -> bool:
    for _, nf in entries:
        if nf.warnings:
            return True
        if nf.source_confidence is not None and nf.source_confidence < LOW_CONFIDENCE:
            return True
    return False


def _shares_token(key_a: str, key_b: str) -> bool:
    return bool(set(key_a.split()) & set(key_b.split()))


def _build_evidence(
        present: list[tuple[NormalizationResult,
                            NormalizedField]]) -> list[FieldEvidence]:
    """Full provenance for every document that carries the field."""
    evidence: list[FieldEvidence] = []
    for norm, nf in present:
        evidence.append(FieldEvidence(
            document_type=norm.document_type,
            source_path=norm.source_path,
            raw_value=nf.raw_value,
            normalized_value=nf.normalized_value,
            comparison_key=nf.comparison_key,
            source_confidence=nf.source_confidence,
            source_bbox=nf.source_bbox,
            normalization_warnings=list(nf.warnings),
        ))
    return evidence


def _values_phrase(
        usable: list[tuple[NormalizationResult, NormalizedField]]) -> str:
    return ", ".join(f"{norm.document_type}={nf.comparison_key!r}"
                     for norm, nf in usable)


def _finding(field: str, decision: str, severity: Severity, reason: str,
             evidence: list[FieldEvidence],
             sim: float | None = None) -> Finding:
    return Finding(
        field=field,
        decision=decision,   # type: ignore[arg-type]
        severity=severity,
        reason=reason,
        similarity=sim,
        evidence=evidence,
        recommended_action=RECOMMENDED_ACTION[(decision, severity)],
    )


# ------------------------------------------------------------- comparisons
def _compare_exact(
        field: str,
        usable: list[tuple[NormalizationResult, NormalizedField]],
        evidence: list[FieldEvidence],
) -> Finding | None:
    """Equal canonical values -> no finding; different -> conflict."""
    keys = sorted({nf.comparison_key for _, nf in usable})
    if len(keys) == 1:
        return None
    reason = (f"{len(usable)} documents disagree on {field}: "
              f"{_values_phrase(usable)}")
    weak = [norm.document_type for norm, nf in usable
            if nf.warnings or (nf.source_confidence is not None
                               and nf.source_confidence < LOW_CONFIDENCE)]
    if weak:
        return _finding(
            field, "review", "LOW",
            reason + "; normalization warning or low OCR confidence "
                     f"(<{LOW_CONFIDENCE:g}) in {', '.join(weak)} - no "
                     "automatic conflict decision from weak evidence",
            evidence)
    return _finding(field, "conflict", CONFLICT_SEVERITY[field], reason,
                    evidence)


def _compare_name(
        field: str,
        usable: list[tuple[NormalizationResult, NormalizedField]],
        evidence: list[FieldEvidence],
) -> Finding | None:
    """Token similarity decides harmless variant / review / conflict."""
    keys = sorted({nf.comparison_key for _, nf in usable})
    if len(keys) == 1:
        return None
    sim = min(similarity(keys[i], keys[j])
              for i in range(len(keys)) for j in range(i + 1, len(keys)))
    values = _values_phrase(usable)

    if sim >= NAME_HARMLESS_MIN and not _has_poor_evidence(usable):
        return _finding(
            field, "harmless_variant", "NONE",
            f"name differs only by a likely spelling/transliteration/"
            f"abbreviation variation (similarity {sim}): {values}",
            evidence, sim)
    if sim >= NAME_REVIEW_MIN:
        return _finding(
            field, "review", "LOW",
        f"name similarity {sim} or weak evidence requires manual review; "
            f"{values}",
            evidence, sim)
    # similarity < 70: unrelated-looking names, unless the evidence is weak
    # and the names still share tokens - then prefer a manual review.
    if _has_poor_evidence(usable) and all(
            _shares_token(keys[i], keys[j])
            for i in range(len(keys)) for j in range(i + 1, len(keys))):
        return _finding(
            field, "review", "LOW",
            f"name similarity {sim} with weak OCR evidence (low confidence or "
            f"normalization warnings); manual review preferred: {values}",
            evidence, sim)
    return _finding(
        field, "conflict", CONFLICT_SEVERITY[field],
        f"names look clearly different (similarity {sim}): {values}",
        evidence, sim)


def _compare_address(
        field: str,
        usable: list[tuple[NormalizationResult, NormalizedField]],
        evidence: list[FieldEvidence],
        conflict_fields: set[str],
) -> Finding | None:
    """Only compare the generic address when city/pincode are clean."""
    if conflict_fields & {"city", "pincode"}:
        # the specific conflict is clearer; a generic address conflict would
        # only duplicate it
        return None
    keys = sorted({nf.comparison_key for _, nf in usable})
    if len(keys) == 1:
        return None
    sim = min(similarity(keys[i], keys[j])
              for i in range(len(keys)) for j in range(i + 1, len(keys)))
    values = _values_phrase(usable)
    if _has_poor_evidence(usable):
        return _finding(
            field, "review", "LOW",
            "address evidence has normalization warnings or low OCR "
            f"confidence; manual review preferred: {values}", evidence, sim)
    if sim >= ADDRESS_HARMLESS_MIN:
        return _finding(
            field, "harmless_variant", "NONE",
            f"city and pincode match and the addresses are equivalent "
            f"modulo ordering/abbreviation (similarity {sim}): {values}",
            evidence, sim)
    return _finding(
        field, "review", "LOW",
        f"city and pincode match but the addresses differ beyond formatting "
        f"(similarity {sim} < {ADDRESS_HARMLESS_MIN:g}): {values}",
        evidence, sim)


# ------------------------------------------------------------------ engine
def compare_fields(
        normalizations: list[NormalizationResult]) -> list[Finding]:
    """Compare every supported field across one bundle's documents."""
    findings: list[Finding] = []
    conflict_fields: set[str] = set()

    for field in COMPARED_FIELDS:
        present = [(norm, norm.fields[field])
                   for norm in normalizations if field in norm.fields]
        if len(present) < 2:
            continue                      # only one document carries it
        evidence = _build_evidence(present)
        usable = [(norm, nf) for norm, nf in present
                  if is_usable(field, nf)]
        if len(usable) < 2:
            findings.append(_finding(
                field, "insufficient_evidence", "NONE",
                f"only {len(usable)} of {len(present)} documents have a "
                f"usable value for {field}; missing or malformed values are "
                f"never turned into a decision",
                evidence))
            continue

        if field in NAME_FIELDS:
            finding = _compare_name(field, usable, evidence)
        elif field == "address":
            finding = _compare_address(field, usable, evidence,
                                       conflict_fields)
        else:
            finding = _compare_exact(field, usable, evidence)

        if finding is not None:
            findings.append(finding)
            if finding.decision == "conflict":
                conflict_fields.add(field)
    return findings


def summarize_findings(findings: list[Finding]) -> dict[str, int | str]:
    """Counts per decision plus the highest severity among the findings."""
    counts = {"conflict": 0, "harmless_variant": 0, "review": 0,
              "insufficient_evidence": 0}
    for finding in findings:
        counts[finding.decision] += 1
    highest = max((f.severity for f in findings),
                  key=lambda s: SEVERITY_ORDER[s], default="NONE")
    return {
        "conflict_count": counts["conflict"],
        "harmless_variant_count": counts["harmless_variant"],
        "review_count": counts["review"],
        "insufficient_evidence_count": counts["insufficient_evidence"],
        "highest_severity": highest,
    }
