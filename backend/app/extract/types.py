"""Typed data models for the field-extraction layer (Step 4)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DocumentType = Literal["id_card", "address_proof", "income_certificate", "unknown"]
FieldStatus = Literal["found", "missing", "ambiguous"]


class ExtractedField(BaseModel):
    """One extracted field with its OCR evidence."""

    value: str | None = None
    confidence: float | None = None
    bbox: list[int] | None = Field(default=None, min_length=4, max_length=4)
    source_words: list[str] = Field(default_factory=list)
    status: FieldStatus = "missing"


class ExtractionResult(BaseModel):
    """Structured extraction output for one document image."""

    source_path: str
    document_type: DocumentType
    fields: dict[str, ExtractedField]
    ocr_word_count: int
    warnings: list[str] = Field(default_factory=list)
