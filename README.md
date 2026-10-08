# AI Document Contradiction Detector

This repository contains a Vite/React frontend and a FastAPI backend for analysing a bundle of citizen-submitted document images. The backend uses OCR, extraction, conservative normalization, and field-specific comparison rules to flag contradictions while retaining raw values, confidence, and source bounding boxes.

All repository documents are synthetic specimens. Do not add real identities or production documents. Ground-truth labels are evaluation-only and are never read during normal analysis.

## Run the backend

In Windows PowerShell:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`:

- `GET /health`
- `GET /health/ocr`
- `GET /api/info`
- `POST /analyze`

Run backend tests with:

```powershell
pytest -q --basetemp .pytest-tmp
```

## Run the frontend

From the repository root:

```powershell
npm install
npm run dev
```

The frontend defaults to `http://localhost:8000`. To target another backend address, create a root `.env` file:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Analysis request

The frontend sends a multipart `POST /analyze` request using the `files` field. Submit 2–10 non-empty PNG, JPG, or JPEG images. PDFs are not supported.

Uploads are processed in a temporary backend directory and removed after analysis. The UI therefore displays returned text evidence, confidence, bounding boxes, and warnings rather than durable image previews.

For the response contract, see [docs/API_CONTRACT.md](docs/API_CONTRACT.md). The frontend is configured to call this API directly.
