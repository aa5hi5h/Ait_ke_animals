import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createCase, getSession } from '../../api/cases.js';
import { reviewerFirstName } from '../../api.js';
import { dashboardText, LANGS } from '../../i18n/dashboardText.js';
import NewCaseDialog from '../../components/dashboard/NewCaseDialog.jsx';

const LANG_KEY = 'yonko_dashboard_lang';

// Standalone route for creating a case (/cases/new). The dashboard opens the
// same component as a modal instead.
export default function NewCasePage() {
  const navigate = useNavigate();
  const session = getSession();

  const [lang, setLang] = useState(() => {
    try {
      return localStorage.getItem(LANG_KEY) || 'en';
    } catch {
      return 'en';
    }
  });
  const t = dashboardText[lang];

  const changeLanguage = (next) => {
    setLang(next);
    try {
      localStorage.setItem(LANG_KEY, next);
    } catch {
      // Language stays for this page load.
    }
  };

  const logout = () => {
    try {
      localStorage.removeItem('yonko_reviewer_session');
    } catch {
      // Session storage unavailable.
    }
    navigate('/');
  };

  const handleCreate = async (data) => {
    const created = await createCase(data);
    navigate(`/cases/${created.id}`);
  };

  return (
    <div className="db-shell">
      <header className="db-header">
        <div className="db-header-left">
          <span className="db-brand">⌘ {t.brand}</span>
          <h1>{t.newCaseTitle}</h1>
        </div>
        <div className="db-header-right">
          <div className="language-picker db-lang" aria-label={t.langLabel}>
            {LANGS.map(([key, label]) => (
              <button
                key={key}
                className={lang === key ? 'active' : ''}
                aria-pressed={lang === key}
                onClick={() => changeLanguage(key)}
              >
                {label}
              </button>
            ))}
          </div>
          <span className="db-reviewer" title={reviewerFirstName(session)}>
            {reviewerFirstName(session)}
          </span>
          <button className="db-btn db-btn-ghost" onClick={logout}>
            {t.logout}
          </button>
        </div>
      </header>

      <main className="db-main db-main-narrow">
        <button className="db-link" onClick={() => navigate('/dashboard')}>
          ← {t.backToDashboard}
        </button>
        <NewCaseDialog
          t={t}
          onSubmit={handleCreate}
          onClose={() => navigate('/dashboard')}
          renderModal={false}
        />
      </main>
    </div>
  );
}
