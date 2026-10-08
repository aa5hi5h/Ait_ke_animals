"""Typed data models for the comparison/detection layer (Step 6)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Decision = Literal["conflict", "harmless_variant", "review",
                   "insufficient_evidence"]
Severity = Literal["HIGH", "MEDIUM", "LOW", "NONE"]

SEVERITY_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}


class DetectionError(Exception):
    """A bundle could not be processed (e.g. fewer than two readable docs)."""


class FieldEvidence(BaseModel):
    """Provenance of one document's value for a compared field."""

    document_type: str
    source_path: str
    raw_value: str | None = None
    normalized_value: str | None = None
    comparison_key: str | None = None
    source_confidence: float | None = None
    source_bbox: list[int] | None = Field(default=None, min_length=4,
                                          max_length=4)
    normalization_warnings: list[str] = Field(default_factory=list)


class Finding(BaseModel):
    """One decision about one field across a bundle's documents."""

    field: str
    decision: Decision
    severity: Severity
    reason: str
    similarity: float | None = None
    evidence: list[FieldEvidence] = Field(default_factory=list)
    recommended_action: str


class BundleDetectionResult(BaseModel):
    """Comparison output for one bundle folder."""

    bundle_path: str
    documents_processed: int
    findings: list[Finding] = Field(default_factory=list)
    summary: dict[str, int | str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
