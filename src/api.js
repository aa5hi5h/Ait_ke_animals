// The FastAPI service is deployed separately from this Vite application.
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

async function readError(response) {
  try {
    const body = await response.json();
    if (body?.detail) {
      return typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    }
  } catch {
    // A non-JSON error response still gets a useful fallback below.
  }
  return `Analysis failed (${response.status} ${response.statusText || 'request error'}).`;
}

export async function analyzeFiles(files) {
  const formData = new FormData();
  Array.from(files).forEach((file) => formData.append('files', file));

  let response;
  try {
    response = await fetch(`${API_BASE_URL}/analyze`, { method: 'POST', body: formData });
  } catch (error) {
    throw new Error(`Could not reach the analysis service at ${API_BASE_URL}. ${error.message}`);
  }

  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}
