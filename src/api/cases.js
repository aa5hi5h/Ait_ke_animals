// Reviewer dashboard data layer.
//
// Every function below resolves after a short delay from src/mock/cases.js so
// the UI works with no backend. Signatures and response shapes are kept
// stable: when FastAPI is ready, replace each body with the equivalent fetch
// against `${API_BASE_URL}` and the components will not need to change.
//
//   listCases(params)                -> { items, total, page, pageSize }
//   createCase(data)                 -> Case
//   getCase(id)                      -> Case
//   updateFinding(caseId, findingId, decision) -> Case
//   updateCaseStatus(id, status)     -> Case
//   saveNotes(id, text)              -> Case
//
// Case shape (wraps the backend Finding / FieldEvidence models):
//   {
//     id, applicantName, applicationType, notes, documentCount,
//     createdAt, updatedAt, status,
//     decisions: { [findingId]: 'pending' | 'accepted' | 'dismissed' },
//     findings:  [{ id, field, severity, values:[{document,value}],
//                   location:{document,field}, explanation }],
//     ignored:   [{ id, field, values:[a,b], reason }]
//   }

import { seedCases } from '../mock/cases.js';

// const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

const DELAY_MS = 380;
const SESSION_KEY = 'yonko_reviewer_session';
const STORE_KEY = 'yonko_cases_store';

const VALID_DECISIONS = new Set(['pending', 'accepted', 'dismissed']);

/** Local reviewer session written by the existing login flow. */
export function getSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    return parsed && parsed.email ? parsed : null;
  } catch {
    return null;
  }
}

/** Flip in the console to exercise the dashboard error + Retry state. */
export function setCasesFailureMode(shouldFail) {
  try {
    localStorage.setItem('yonko_cases_force_error', shouldFail ? '1' : '0');
  } catch {
    // Storage unavailable: failure mode simply stays off.
  }
}

function failureMode() {
  try {
    return localStorage.getItem('yonko_cases_force_error') === '1';
  } catch {
    return false;
  }
}

const wait = (ms = DELAY_MS) => new Promise((resolve) => setTimeout(resolve, ms));

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function readStore() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length) return parsed;
    }
  } catch {
    // Fall through to the seed data.
  }
  return clone(seedCases);
}

function writeStore(cases) {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(cases));
  } catch {
    // Private mode: the store stays in memory for this page load only.
  }
  return cases;
}

let memoryStore = null;

function store() {
  if (!memoryStore) memoryStore = readStore();
  return memoryStore;
}

function persist() {
  memoryStore = writeStore(store());
  return memoryStore;
}

/** Restore the seeded demo data (used by the dashboard error Retry path). */
export function resetCaseStore() {
  memoryStore = clone(seedCases);
  persist();
  return memoryStore;
}

async function respond(makeValue) {
  await wait();
  if (failureMode()) {
    throw new Error('Could not load cases. The case service did not respond.');
  }
  return makeValue();
}

function sortNewestFirst(cases) {
  return [...cases].sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
}

function findCase(id) {
  const found = store().find((item) => item.id === id);
  if (!found) throw new Error(`Case ${id} was not found.`);
  return found;
}

function touch(item) {
  item.updatedAt = new Date().toISOString();
  return item;
}

const SEVERITY_RANK = { HIGH: 3, MEDIUM: 2, LOW: 1, NONE: 0 };

/**
 * Derive the case status from the current findings and decisions.
 * draft/processing are preserved until an analysis has produced findings.
 */
export function deriveStatus(item) {
  if (!item.findings.length) {
    return item.status === 'cleared' ? 'cleared' : item.status;
  }

  const pending = item.findings.filter(
    (f) => (item.decisions?.[f.id] || 'pending') === 'pending'
  );

  if (!pending.length) return 'cleared';

  const highest = pending.reduce(
    (rank, f) => (SEVERITY_RANK[f.severity] > rank ? SEVERITY_RANK[f.severity] : rank),
    0
  );

  return highest >= SEVERITY_RANK.HIGH ? 'conflicts_found' : 'needs_review';
}

export function conflictCount(item) {
  return item.findings.length;
}

export function statusCounts(cases) {
  return {
    total: cases.length,
    needsReview: cases.filter((c) => c.status === 'needs_review').length,
    conflictsFound: cases.filter((c) => c.status === 'conflicts_found').length,
    cleared: cases.filter((c) => c.status === 'cleared').length,
  };
}

/**
 * @param {{query?: string, status?: string, page?: number, pageSize?: number}} params
 * @returns {Promise<{items: object[], total: number, page: number, pageSize: number,
 *                    counts: {total, needsReview, conflictsFound, cleared}}>}
 *
 * `counts` always describes the whole case list (unfiltered), so the summary
 * cards stay correct while the table below is searched or filtered.
 */
export async function listCases(params = {}) {
  const { query = '', status = 'all', page = 1, pageSize = 6 } = params;

  return respond(() => {
    const counts = statusCounts(store());

    const needle = String(query).trim().toLowerCase();

    const filtered = sortNewestFirst(store()).filter((item) => {
      const matchesQuery =
        !needle ||
        item.id.toLowerCase().includes(needle) ||
        item.applicantName.toLowerCase().includes(needle);
      const matchesStatus = status === 'all' || item.status === status;
      return matchesQuery && matchesStatus;
    });

    const start = (page - 1) * pageSize;
    return {
      items: clone(filtered.slice(start, start + pageSize)),
      total: filtered.length,
      page,
      pageSize,
      counts,
    };
  });
}

/**
 * @param {{applicantName: string, applicationType: string, notes?: string}} data
 * @returns {Promise<object>} the created case, status "draft"
 */
export async function createCase(data) {
  const applicantName = String(data?.applicantName || '').trim();
  const applicationType = String(data?.applicationType || '').trim();

  return respond(() => {
    if (!applicantName) throw new Error('Applicant name is required.');
    if (!applicationType) throw new Error('Application type is required.');

    const all = store();
    const highestId = all.reduce((max, item) => {
      const value = Number(String(item.id).replace(/\D/g, ''));
      return Number.isFinite(value) && value > max ? value : max;
    }, 1000);

    const timestamp = new Date().toISOString();
    const created = {
      id: `CASE-${highestId + 1}`,
      applicantName,
      applicationType,
      notes: String(data?.notes || '').trim(),
      documentCount: 0,
      createdAt: timestamp,
      updatedAt: timestamp,
      status: 'draft',
      decisions: {},
      findings: [],
      ignored: [],
    };

    all.unshift(created);
    persist();
    return clone(created);
  });
}

/**
 * @param {string} id
 * @returns {Promise<object>}
 */
export async function getCase(id) {
  return respond(() => clone(findCase(id)));
}

/**
 * @param {string} caseId
 * @param {string} findingId
 * @param {'pending'|'accepted'|'dismissed'} decision
 * @returns {Promise<object>} the updated case
 */
export async function updateFinding(caseId, findingId, decision) {
  return respond(() => {
    if (!VALID_DECISIONS.has(decision)) {
      throw new Error(`Unknown decision: ${decision}`);
    }

    const item = findCase(caseId);
    item.decisions = { ...(item.decisions || {}), [findingId]: decision };
    item.status = deriveStatus(item);
    touch(item);
    persist();
    return clone(item);
  });
}

/**
 * @param {string} id
 * @param {'draft'|'processing'|'needs_review'|'conflicts_found'|'cleared'} status
 * @returns {Promise<object>} the updated case
 */
export async function updateCaseStatus(id, status) {
  return respond(() => {
    const item = findCase(id);
    item.status = status;
    touch(item);
    persist();
    return clone(item);
  });
}

/**
 * @param {string} id
 * @param {string} text
 * @returns {Promise<object>} the updated case
 */
export async function saveNotes(id, text) {
  return respond(() => {
    const item = findCase(id);
    item.notes = String(text || '');
    touch(item);
    persist();
    return clone(item);
  });
}

/**
 * Extra (beyond the six specified functions): store the result of the existing
 * document analysis page on the case so the report below it, and the dashboard
 * counts above it, stay in sync.
 *
 * Finding ids are rebuilt with the same `${field}-${index}` rule the analysis
 * page uses, so reviewer decisions map onto the same keys after a reload.
 *
 * @param {string} id
 * @param {{documents_processed?: number, findings?: object[], warnings?: string[]}} analysis
 * @returns {Promise<object>} the updated case
 */
export async function attachAnalysis(id, analysis) {
  return respond(() => {
    const item = findCase(id);
    const source = analysis?.findings || [];

    item.documentCount = analysis?.documents_processed ?? item.documentCount;

    item.findings = source
      .filter((entry) => entry.decision !== 'harmless_variant')
      .map((entry, index) => ({
        id: `${entry.field}-${index}`,
        field: entry.field,
        severity: (entry.severity || 'NONE').toUpperCase(),
        values: (entry.evidence || []).map((evidence) => ({
          document: evidence.document_type,
          value: evidence.raw_value || evidence.normalized_value || '—',
        })),
        location: {
          document: entry.evidence?.[0]?.document_type || '—',
          field: String(entry.field)
            .replace(/_/g, ' ')
            .toLowerCase()
            .replace(/^./, (letter) => letter.toUpperCase()),
        },
        explanation: entry.reason || entry.recommended_action || '',
      }));

    const harmless = source
      .filter((entry) => entry.decision === 'harmless_variant')
      .map((entry, index) => ({
        id: `harmless-${index}`,
        field: entry.field,
        values: (entry.evidence || [])
          .map((evidence) => evidence.raw_value || evidence.normalized_value)
          .filter(Boolean),
        reason: entry.reason || '',
      }));

    const seen = new Set();
    item.ignored = [...item.ignored, ...harmless].filter((entry) => {
      const key = `${entry.field}|${(entry.values || []).join('|')}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    // Preserve decisions already made for findings that came back again.
    item.decisions = item.decisions || {};
    item.findings.forEach((entry) => {
      if (!item.decisions[entry.id]) item.decisions[entry.id] = 'pending';
    });

    item.status = deriveStatus(item);
    touch(item);
    persist();
    return clone(item);
  });
}
