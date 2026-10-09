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

// Reviewer sign in / sign up.
//
// The FastAPI service currently exposes /health, /api/info and /analyze only,
// so reviewer accounts are kept in this browser session for the demo. When the
// backend adds its auth route, replace the body of these two functions with the
// same request() pattern used by analyzeFiles and keep the returned shape:
//   { email: string }
const ACCOUNTS_KEY = 'yonko_reviewer_accounts';

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function readAccounts() {
  try {
    return JSON.parse(localStorage.getItem(ACCOUNTS_KEY)) || {};
  } catch {
    return {};
  }
}

function writeAccounts(accounts) {
  try {
    localStorage.setItem(ACCOUNTS_KEY, JSON.stringify(accounts));
  } catch {
    // Storage can be unavailable in private mode; the demo still proceeds.
  }
}

function validateCredentials({ email, password }) {
  const normalized = String(email || '').trim().toLowerCase();

  if (!EMAIL_PATTERN.test(normalized)) {
    throw new Error('Enter a valid official email address, for example reviewer@department.gov.in.');
  }
  if (String(password || '').length < 8) {
    throw new Error('Password must be at least 8 characters long.');
  }

  return normalized;
}

export async function signUpReviewer({ email, password }) {
  const normalized = validateCredentials({ email, password });
  await delay(400);

  const accounts = readAccounts();
  if (accounts[normalized]) {
    throw new Error('An account already exists for this email. Sign in instead.');
  }

  accounts[normalized] = { email: normalized, createdAt: new Date().toISOString() };
  writeAccounts(accounts);
  return { email: normalized };
}

export async function signInReviewer({ email, password }) {
  const normalized = validateCredentials({ email, password });
  await delay(400);

  const accounts = readAccounts();
  if (!accounts[normalized]) {
    // Demo convenience: the first sign in with a valid email provisions a
    // reviewer account, so the workspace is never unreachable during judging.
    accounts[normalized] = { email: normalized, createdAt: new Date().toISOString() };
    writeAccounts(accounts);
  }

  const account = accounts[normalized];
  return {
    email: account.email,
    name: account.name || '',
    dob: account.dob || '',
    // Older / freshly provisioned accounts never answered the basic questions.
    needsProfile: !account.name,
  };
}

// Basic information collected once, right after the first sign up (or the
// first sign in for accounts that predate this step).
export async function saveProfile({ email, name, dob }) {
  const normalized = String(email || '').trim().toLowerCase();
  const cleanName = String(name || '').trim().replace(/\s+/g, ' ');
  const cleanDob = String(dob || '').trim();

  if (cleanName.length < 2) throw new Error('Enter your full name.');
  if (!cleanDob) throw new Error('Enter your date of birth.');
  if (Number.isNaN(new Date(cleanDob).getTime())) {
    throw new Error('Enter a valid date of birth.');
  }

  await delay(300);

  const accounts = readAccounts();
  if (!accounts[normalized]) throw new Error('Account not found. Please sign in again.');

  accounts[normalized] = { ...accounts[normalized], name: cleanName, dob: cleanDob };
  writeAccounts(accounts);
  return { email: accounts[normalized].email, name: cleanName, dob: cleanDob };
}

// The reviewer UI shows a first name, never the raw email address.
export function reviewerFirstName(account) {
  const name = String(account?.name || '').trim();
  if (name) return name.split(/\s+/)[0];

  const letters = String(account?.email || '')
    .split('@')[0]
    .replace(/[^A-Za-z]+/g, ' ')
    .trim();
  if (letters) return letters.split(/\s+/)[0].replace(/^./, (c) => c.toUpperCase());
  return 'Reviewer';
}

export function reviewerInitials(account) {
  const name = String(account?.name || '').trim();
  if (name) {
    const parts = name.split(/\s+/);
    const first = parts[0];
    const letters =
      parts.length > 1 ? first[0] + parts[parts.length - 1][0] : first.slice(0, 2);
    return letters.toUpperCase();
  }

  const letters = String(account?.email || '')
    .split('@')[0]
    .replace(/[^A-Za-z]/g, '');
  return (letters.slice(0, 2) || 'RV').toUpperCase();
}
