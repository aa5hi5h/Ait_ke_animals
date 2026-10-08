"""Typed data models for the OCR pipeline (Step 3).

All bounding boxes are [x1, y1, x2, y2] pixels in the ORIGINAL input image
coordinate system, regardless of any preprocessing/upscaling applied.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class OCRError(Exception):
    """Raised when an image cannot be read or Tesseract cannot run."""


class OCRWord(BaseModel):
    """One recognized word."""

    text: str
    confidence: float
    bbox: list[int] = Field(min_length=4, max_length=4,
                            description="[x1, y1, x2, y2] in original image pixels")
    page: int = 1


class OCRResult(BaseModel):
    """Full OCR output for a single input image."""

    source_path: str
    full_text: str
    words: list[OCRWord]
    language: str
    preprocessing_applied: list[str]
