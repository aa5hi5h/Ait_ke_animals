"""Conservative document preprocessing with OpenCV (Step 3).

The synthetic documents are already clean, so this pipeline only applies
mild steps and NEVER crops: grayscale -> optional upscale -> mild denoise ->
contrast improvement -> Otsu threshold. The visible "SPECIMEN - SYNTHETIC"
watermark stays in the image; it is expected in raw OCR output and will be
ignored later during extraction.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from app.ocr.types import OCRError

# upscale (x2) only when the image's smallest side is below this many pixels
SMALL_IMAGE_MIN_SIDE = 800
DENOISE_KERNEL = 3           # median blur ksize=3 = mild
CLAHE_CLIP_LIMIT = 2.0


@dataclass(frozen=True)
class PreprocessResult:
    image: np.ndarray      # image that should be handed to Tesseract
    operations: list[str]  # exact operations that were applied, in order
    scale: float           # processed/original scale factor (1.0 = unchanged)


def load_image(path: Path | str) -> np.ndarray:
    """Read an image as BGR, with clear errors for missing/corrupt files.

    Uses np.fromfile + cv2.imdecode instead of cv2.imread so Unicode paths
    work on Windows.
    """
    p = Path(path)
    if not p.is_file():
        raise OCRError(f"Image not found: {p}")
    try:
        buffer = np.fromfile(str(p), dtype=np.uint8)
    except OSError as exc:
        raise OCRError(f"Could not read image file {p}: {exc}") from exc
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise OCRError(f"Could not decode image (unsupported or corrupt file): {p}")
    return image


def preprocess_image(image: np.ndarray) -> PreprocessResult:
    """Apply mild preprocessing. Never crops; never changes image size
    unless the input is small (then it is upscaled 2x)."""
    operations: list[str] = []

    # grayscale
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        operations.append("grayscale")
    else:
        gray = image

    # optional upscale, only for small images
    scale = 1.0
    if min(gray.shape[:2]) < SMALL_IMAGE_MIN_SIDE:
        scale = 2.0
        gray = cv2.resize(gray, None, fx=scale, fy=scale,
                          interpolation=cv2.INTER_CUBIC)
        operations.append(f"upscale_{scale:g}x")

    # mild denoise
    gray = cv2.medianBlur(gray, DENOISE_KERNEL)
    operations.append("denoise_median_blur")

    # contrast improvement
    gray = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT,
                           tileGridSize=(8, 8)).apply(gray)
    operations.append("clahe_contrast")

    # binarize (Otsu)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    operations.append("otsu_threshold")
    if cv2.mean(binary)[0] < 127:      # mostly dark -> keep text dark-on-white
        binary = cv2.bitwise_not(binary)
        operations.append("invert")

    return PreprocessResult(image=binary, operations=operations, scale=scale)
