// Backend integration boundary. Set VITE_API_BASE_URL when the FastAPI service is available.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options
  });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.status === 204 ? null : response.json();
}

export const createBundle = (files) => {
  const body = new FormData();
  files.forEach(file => body.append('files', file));
  return fetch(`${API_BASE_URL}/bundles`, { method: 'POST', body }).then(async response => {
    if (!response.ok) throw new Error(`Upload failed: ${response.status}`);
    return response.json();
  });
};

export const analyzeBundle = (bundleId) => request(`/bundles/${bundleId}/analyze`, { method: 'POST' });
export const getBundle = (bundleId) => request(`/bundles/${bundleId}`);
export const updateFinding = (findingId, status) => request(`/findings/${findingId}`, { method: 'PATCH', body: JSON.stringify({ status }) });
export const updateField = (fieldId, value) => request(`/fields/${fieldId}`, { method: 'PATCH', body: JSON.stringify({ value }) });
export const getDocumentImage = (documentId) => `${API_BASE_URL}/documents/${documentId}/image`;
