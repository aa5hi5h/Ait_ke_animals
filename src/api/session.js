const SESSION_KEY = 'yonko_reviewer_session';

export function getSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    return parsed && parsed.email && parsed.token ? parsed : null;
  } catch {
    return null;
  }
}

export function setSession(account) {
  try {
    localStorage.setItem(SESSION_KEY, JSON.stringify(account));
  } catch {
    // Storage can be unavailable in private mode.
  }
}

export function clearSession() {
  try {
    localStorage.removeItem(SESSION_KEY);
  } catch {
    // Ignore storage delete errors.
  }
}

export function authHeaders() {
  const session = getSession();
  return session?.token ? { Authorization: `Bearer ${session.token}` } : {};
}
