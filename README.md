# AI Document Contradiction Detector — Frontend

This Vite + React frontend sends document images to the FastAPI analysis service, which must run separately.

## Run locally

```bash
npm install
npm run dev
```

By default, the frontend calls `http://localhost:8000`. To use another backend address, create a `.env` file in this folder:

```env
VITE_API_BASE_URL=http://localhost:8000
```

The current backend accepts only **2–10 non-empty PNG, JPG, or JPEG images** for `POST /analyze`. PDFs are not supported. Uploaded images are deleted by the backend after analysis, so the frontend intentionally shows evidence as returned text, confidence, bounding boxes, and normalization warnings rather than attempting image previews.
