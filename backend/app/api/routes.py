"""HTTP routes for temporary, privacy-preserving document analysis."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.detect.engine import detect_bundle
from app.detect.types import DetectionError
from app.ocr.types import OCRError

router = APIRouter(tags=["analysis"])

MIN_FILES = 2
MAX_FILES = 10
ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg"}


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.get("/api/info")
def api_info() -> dict[str, object]:
    """Describe the upload contract without exposing any user data."""
    return {
        "project_name": "AI Document Contradiction Detector",
        "supported_file_types": sorted(ALLOWED_SUFFIXES),
        "minimum_file_count": MIN_FILES,
        "maximum_file_count": MAX_FILES,
        "image_only": True,
        "synthetic_demo_data_only": True,
    }


@router.post("/analyze")
async def analyze(files: list[UploadFile] = File(...)) -> dict[str, object]:
    """Analyze 2--10 images in a request-scoped temporary directory."""
    if not MIN_FILES <= len(files) <= MAX_FILES:
        raise _bad_request(f"Upload between {MIN_FILES} and {MAX_FILES} image files.")

    names: list[str] = []
    for upload in files:
        filename = upload.filename or ""
        suffix = Path(filename).suffix.lower()
        if not filename.strip():
            raise _bad_request("Each upload must have a filename.")
        if suffix not in ALLOWED_SUFFIXES:
            raise _bad_request("Only PNG, JPG, and JPEG image files are supported.")
        if upload.content_type and not upload.content_type.lower().startswith("image/"):
            raise _bad_request("Each upload must declare an image content type.")
        names.append(filename)
    if len({name.casefold() for name in names}) != len(names):
        raise _bad_request("Duplicate filenames are not allowed in one upload.")

    temp_dir = Path(tempfile.mkdtemp(prefix="document-analysis-"))
    try:
        for index, upload in enumerate(files):
            # Do not use client paths.  An index prevents traversal and keeps
            # ordering deterministic while retaining the genuine extension.
            suffix = Path(upload.filename or "").suffix.lower()
            destination = temp_dir / f"upload_{index:02d}{suffix}"
            contents = await upload.read()
            if not contents:
                raise _bad_request(f"Uploaded file '{upload.filename}' is empty.")
            destination.write_bytes(contents)

        # The detector works from PNGs. Convert supported JPEG uploads only in
        # the private temp directory, then remove the originals immediately.
        from PIL import Image
        for image_path in list(temp_dir.iterdir()):
            if image_path.suffix.lower() in {".jpg", ".jpeg"}:
                png_path = image_path.with_suffix(".png")
                try:
                    with Image.open(image_path) as image:
                        image.convert("RGB").save(png_path, "PNG")
                except Exception as exc:
                    raise _bad_request(
                        f"Uploaded file '{image_path.name}' is not a readable image.") from exc
                image_path.unlink()

        result = detect_bundle(temp_dir)
        return result.model_dump()
    except HTTPException:
        raise
    except (DetectionError, OCRError) as exc:
        raise _bad_request(f"Unable to analyze the submitted documents: {exc}") from exc
    except Exception as exc:
        # Keep implementation details and tracebacks out of HTTP responses.
        raise HTTPException(status_code=500, detail="Document analysis failed.") from exc
    finally:
        for upload in files:
            await upload.close()
        shutil.rmtree(temp_dir, ignore_errors=True)
