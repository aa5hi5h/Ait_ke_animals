// Reviewer dashboard data layer.
//
// Cases are stored per signed-in reviewer in the SQLite database behind
// FastAPI. Signatures match the previous local store so the dashboard
// components do not need to change.
//
//   listCases(params)                -> { items, total, page, pageSize }
//   createCase(data)                 -> Case
//   getCase(id)                      -> Case
//   updateFinding(caseId, findingId, decision) -> Case
//   updateCaseStatus(id, status)     -> Case
//   saveNotes(id, text)              -> Case

import { seedCases } from '../mock/cases.js';
import { API_BASE_URL } from '../api.js';
import { authHeaders, getSession } from './session.js';

export { getSession };

const SEED_IDS = new Set(seedCases.map((item) => item.id));
const LEGACY_STORE_KEY = 'yonko_cases_store';
const MIGRATED_KEY = 'yonko_cases_legacy_migrated';

async function readError(response) {
  try {
    const body = await response.json();
    if (body?.detail) {
      return typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    }
  } catch {
    // Fall through.
  }
  return `Case request failed (${response.status} ${response.statusText || 'request error'}).`;
}

async function request(path, { method = 'GET', body } = {}) {
  const session = getSession();
  if (!session?.token) {
    throw new Error('Sign in required.');
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: {
        ...(body ? { 'Content-Type': 'application/json' } : {}),
        ...authHeaders(),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    throw new Error(
      `Could not reach the case database at ${API_BASE_URL}. Start the backend and try again.`
    );
  }

  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

function readLegacyCustomCases() {
  try {
    const raw = localStorage.getItem(LEGACY_STORE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item) => item && !SEED_IDS.has(item.id));
  } catch {
    return [];
  }
}

/**
 * Move real locally created cases (for example Piyush) onto the signed-in
 * reviewer. Demo seed applicants are never imported, and a brand-new sign-up
 * does not inherit another reviewer's work.
 */
export async function migrateLocalCasesIfNeeded() {
  try {
    if (localStorage.getItem(MIGRATED_KEY) === '1') return;
    if (sessionStorage.getItem('yonko_just_signed_up') === '1') return;
  } catch {
    return;
  }

  const custom = readLegacyCustomCases();
  if (!custom.length) {
    try {
      localStorage.removeItem(LEGACY_STORE_KEY);
      localStorage.setItem(MIGRATED_KEY, '1');
    } catch {
      // Ignore storage errors.
    }
    return;
  }

  for (const item of custom) {
    await request('/cases/import', { method: 'POST', body: { case: item } });
  }

  try {
    localStorage.removeItem(LEGACY_STORE_KEY);
    localStorage.setItem(MIGRATED_KEY, '1');
  } catch {
    // Ignore storage errors.
  }
}

export function setCasesFailureMode(shouldFail) {
  try {
    localStorage.setItem('yonko_cases_force_error', shouldFail ? '1' : '0');
  } catch {
    // Storage unavailable.
  }
}

export function resetCaseStore() {
  // Server-backed stores are not reset to demo seed data.
  return [];
}

export function deriveStatus(item) {
  if (!item.findings.length) {
    return item.status === 'cleared' ? 'cleared' : item.status;
  }

  const pending = item.findings.filter(
    (finding) => (item.decisions?.[finding.id] || 'pending') === 'pending'
  );
  if (!pending.length) return 'cleared';

  const rank = { HIGH: 3, MEDIUM: 2, LOW: 1, NONE: 0 };
  const highest = pending.reduce(
    (score, finding) => (rank[finding.severity] > score ? rank[finding.severity] : score),
    0
  );
  return highest >= rank.HIGH ? 'conflicts_found' : 'needs_review';
}

export function conflictCount(item) {
  return item.findings.length;
}

export function statusCounts(cases) {
  return {
    total: cases.length,
    needsReview: cases.filter((item) => item.status === 'needs_review').length,
    conflictsFound: cases.filter((item) => item.status === 'conflicts_found').length,
    cleared: cases.filter((item) => item.status === 'cleared').length,
  };
}

export async function listCases(params = {}) {
  const { query = '', status = 'all', page = 1, pageSize = 6 } = params;
  await migrateLocalCasesIfNeeded();
  const search = new URLSearchParams({
    query,
    status,
    page: String(page),
    pageSize: String(pageSize),
  });
  return request(`/cases?${search.toString()}`);
}

export async function createCase(data) {
  return request('/cases', {
    method: 'POST',
    body: {
      applicantName: data?.applicantName,
      applicationType: data?.applicationType,
      notes: data?.notes || '',
    },
  });
}

export async function getCase(id) {
  return request(`/cases/${encodeURIComponent(id)}`);
}

export async function updateFinding(caseId, findingId, decision) {
  return request(
    `/cases/${encodeURIComponent(caseId)}/findings/${encodeURIComponent(findingId)}`,
    { method: 'PATCH', body: { decision } }
  );
}

export async function updateCaseStatus(id, status) {
  return request(`/cases/${encodeURIComponent(id)}/status`, {
    method: 'PATCH',
    body: { status },
  });
}

export async function saveNotes(id, text) {
  return request(`/cases/${encodeURIComponent(id)}/notes`, {
    method: 'PATCH',
    body: { notes: text || '' },
  });
}

export async function attachAnalysis(id, analysis) {
  return request(`/cases/${encodeURIComponent(id)}/analysis`, {
    method: 'POST',
    body: {
      documents_processed: analysis?.documents_processed,
      findings: analysis?.findings || [],
      warnings: analysis?.warnings || [],
    },
  });
}
