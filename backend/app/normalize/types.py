"""Typed data models for the normalization layer (Step 5)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NormalizedField(BaseModel):
    """One normalized field: raw evidence plus its safe comparison forms.

    `raw_value`, `source_confidence` and `source_bbox` mirror the extraction
    output and are never rewritten by this layer.
    """

    raw_value: str | None = None
    normalized_value: str | None = None
    comparison_key: str | None = None
    field_type: str
    transformations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source_confidence: float | None = None
    source_bbox: list[int] | None = Field(default=None, min_length=4,
                                          max_length=4)


class NormalizationResult(BaseModel):
    """Normalization output for one document."""

    source_path: str
    document_type: str
    fields: dict[str, NormalizedField]
    warnings: list[str] = Field(default_factory=list)
