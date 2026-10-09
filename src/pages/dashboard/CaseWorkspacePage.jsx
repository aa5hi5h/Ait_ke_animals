import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Workspace } from '../../main.jsx';
import {
  getSession,
  getCase,
  updateFinding,
  updateCaseStatus,
  saveNotes,
  attachAnalysis,
} from '../../api/cases.js';
import { signOutReviewer } from '../../api.js';
import { clearSession } from '../../api/session.js';
import { dashboardText } from '../../i18n/dashboardText.js';
import CaseReport from '../../components/dashboard/CaseReport.jsx';
import { ErrorState, SkeletonRows } from '../../components/dashboard/StateBlocks.jsx';

const LANG_KEY = 'yonko_dashboard_lang';

// /cases/:caseId
// TOP:  the existing document analysis page (Workspace), rendered unchanged.
// BELOW: the new Case report, kept in sync through attachAnalysis().
export default function CaseWorkspacePage() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const session = getSession();

  useEffect(() => {
    if (!session?.token) navigate('/');
  }, [session, navigate]);

  const [lang, setLang] = useState(() => {
    try {
      return localStorage.getItem(LANG_KEY) || 'en';
    } catch {
      return 'en';
    }
  });
  const t = dashboardText[lang];

  const [caseItem, setCaseItem] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [view, setView] = useState('analysis');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    setAnalysis(null);
    setView('analysis');

    (async () => {
      try {
        const loaded = await getCase(caseId);
        if (!cancelled) setCaseItem(loaded);
      } catch (requestError) {
        if (!cancelled) setError(requestError.message || 'Case could not be loaded.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [caseId, reloadKey]);

  const changeLanguage = (next) => {
    setLang(next);
    try {
      localStorage.setItem(LANG_KEY, next);
    } catch {
      // Language stays for this page load.
    }
  };

  const logout = () => {
    signOutReviewer();
    clearSession();
    navigate('/');
  };

  // Fired by the existing analysis page. Persists the result on the case so
  // the report below, and the dashboard counts, stay consistent.
  const handleAnalysis = useCallback(
    async (result) => {
      setAnalysis(result);
      try {
        const updated = await attachAnalysis(caseId, result);
        setCaseItem(updated);
      } catch {
        // The report still shows the live result; persistence can be retried.
      }
    },
    [caseId]
  );

  const handleDecision = useCallback(
    async (findingId, decision) => {
      if (!caseItem) return;

      // Optimistic: the summary and status must move immediately.
      const previous = caseItem;
      setCaseItem({
        ...caseItem,
        decisions: { ...(caseItem.decisions || {}), [findingId]: decision },
      });

      try {
        const updated = await updateFinding(caseId, findingId, decision);
        setCaseItem((current) => ({ ...updated, notes: current?.notes ?? updated.notes }));
      } catch {
        setCaseItem(previous);
      }
    },
    [caseId, caseItem]
  );

  const handleStatusChange = useCallback(
    async (status) => {
      const updated = await updateCaseStatus(caseId, status);
      setCaseItem(updated);
    },
    [caseId]
  );

  const handleNotesSave = useCallback(
    async (text) => {
      const updated = await saveNotes(caseId, text);
      setCaseItem(updated);
    },
    [caseId]
  );

  if (loading && !caseItem) {
    return (
      <div className="db-shell">
        <main className="db-main">
          <SkeletonRows rows={4} />
        </main>
      </div>
    );
  }

  if (error && !caseItem) {
    return (
      <div className="db-shell">
        <main className="db-main">
          <ErrorState
            title={t.errorTitle}
            message={error}
            retryLabel={t.retry}
            onRetry={() => setReloadKey((key) => key + 1)}
          />
          <div className="db-report-actions">
            <button className="db-btn" onClick={() => navigate('/dashboard')}>
              ← {t.backToDashboard}
            </button>
          </div>
        </main>
      </div>
    );
  }

  if (!caseItem) return null;

  return (
    <div className="db-case-workspace">
      {/* The existing document analysis page, with "Case Report" added to its
          sidebar. Both views share the same shell, so the reviewer can flip
          between them without losing the analysis. */}
      <Workspace
        reviewer={session || { email: 'Reviewer' }}
        onSignOut={logout}
        onPrecheck={() => navigate('/')}
        onAnalysisChange={handleAnalysis}
        activeView={view}
        onViewChange={setView}
        lang={lang}
        onLangChange={changeLanguage}
        caseBar={
          <div className="db-casebar">
            <button className="db-link" onClick={() => navigate('/dashboard')}>
              ← {t.backToDashboard}
            </button>
            <span className="db-casebar-id">
              {caseItem.id} · {caseItem.applicantName}
            </span>
            <span className="db-casebar-type">{caseItem.applicationType}</span>
          </div>
        }
        reportSlot={
          <CaseReport
            caseItem={caseItem}
            analysis={analysis}
            t={t}
            lang={lang}
            onDecision={handleDecision}
            onStatusChange={handleStatusChange}
            onNotesSave={handleNotesSave}
            onBack={() => navigate('/dashboard')}
          />
        }
      />
    </div>
  );
}
