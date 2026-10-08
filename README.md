# AI Document Contradiction Detector

This backend compares statements extracted from a group of citizen-submitted document images. It uses OCR, extraction, conservative normalization, and field-specific rules to flag genuine contradictions while preserving raw values, OCR confidence, and source bounding boxes for review.

All repository documents are synthetic specimens. Do not add real identities or production documents. Ground-truth labels are evaluation-only and are never read during normal detection or API analysis.

## Windows PowerShell setup

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

In a second PowerShell window (also from `backend`):

```powershell
pytest -q --basetemp .pytest-tmp
```

`--basetemp` keeps pytest temporary files inside the project on restricted Windows environments.

## API

- `GET /health` — service status
- `GET /health/ocr` — Tesseract availability and languages
- `GET /api/info` — supported upload contract
- `POST /analyze` — multipart `files` field containing 2–10 PNG/JPG/JPEG files

Uploads are copied to a request-scoped temporary directory, processed, and deleted even if analysis fails. The backend never saves uploaded originals in the project data folders.

PowerShell example using three synthetic images:

```powershell
curl.exe -X POST http://127.0.0.1:8000/analyze `
  -F "files=@data/synthetic/bundle_0001/id_card.png;type=image/png" `
  -F "files=@data/synthetic/bundle_0001/address_proof.png;type=image/png" `
  -F "files=@data/synthetic/bundle_0001/income_certificate.png;type=image/png"
```

Equivalent PowerShell request:

```powershell
$form = @{
  files = @(
    Get-Item data/synthetic/bundle_0001/id_card.png,
    Get-Item data/synthetic/bundle_0001/address_proof.png,
    Get-Item data/synthetic/bundle_0001/income_certificate.png
  )
}
Invoke-RestMethod -Uri http://127.0.0.1:8000/analyze -Method Post -Form $form
```

A successful response contains `documents_processed`, a `findings` array, and a summary such as `{ "conflict_count": 1, "review_count": 0, "highest_severity": "HIGH" }`.

The planned React frontend should call `POST /analyze`; see [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) for the response contract.

## Detector CLI

From `backend`:

```powershell
python -m app.detect.engine data/synthetic/bundle_0001 --output data/detection_results/bundle_0001.json
python -m app.detect.engine --evaluate data --output data/detection_results/evaluation_report.json
```
