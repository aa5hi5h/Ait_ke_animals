import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listCases, createCase, getSession } from '../../api/cases.js';
import { reviewerFirstName } from '../../api.js';
import { dashboardText, LANGS } from '../../i18n/dashboardText.js';
import SummaryCards from '../../components/dashboard/SummaryCards.jsx';
import CaseTable from '../../components/dashboard/CaseTable.jsx';
import NewCaseDialog from '../../components/dashboard/NewCaseDialog.jsx';
import { SkeletonRows, EmptyState, ErrorState } from '../../components/dashboard/StateBlocks.jsx';

const LANG_KEY = 'yonko_dashboard_lang';
const PAGE_SIZE = 6;

export default function DashboardPage() {
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

  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [counts, setCounts] = useState(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('all');
  const [showNew, setShowNew] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  const searchRef = useRef(null);

  const changeLanguage = (next) => {
    setLang(next);
    try {
      localStorage.setItem(LANG_KEY, next);
    } catch {
      // Language simply stays for this page load.
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

  // First page whenever the search or status filter changes.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');

    const timer = window.setTimeout(async () => {
      try {
        const response = await listCases({ query, status, page: 1, pageSize: PAGE_SIZE });
        if (cancelled) return;
        setItems(response.items);
        setTotal(response.total);
        setCounts(response.counts || null);
        setPage(1);
      } catch (requestError) {
        if (!cancelled) {
          setItems([]);
          setError(requestError.message);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, query ? 250 : 0);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [query, status, reloadKey]);

  const loadMore = useCallback(async () => {
    const next = page + 1;
    setLoading(true);
    try {
      const response = await listCases({ query, status, page: next, pageSize: PAGE_SIZE });
      setItems((current) => [...current, ...response.items]);
      setTotal(response.total);
      setCounts(response.counts || null);
      setPage(next);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, [page, query, status]);

  const handleCreate = async (data) => {
    const created = await createCase(data);
    navigate(`/cases/${created.id}`);
  };

  const openCase = (id) => navigate(`/cases/${id}`);

  const canLoadMore = items.length < total;
  const showEmpty = !loading && !error && items.length === 0;

  return (
    <div className="db-shell">
      <header className="db-header">
        <div className="db-header-left">
          <span className="db-brand">⌘ {t.brand}</span>
          <h1>{t.title}</h1>
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
          <button className="db-btn db-btn-primary" onClick={() => setShowNew(true)}>
            {t.newCase}
          </button>
        </div>
      </header>

      <main className="db-main">
        <p className="db-subtitle">{t.subtitle}</p>

        <SummaryCards cases={items} counts={counts} t={t} />

        <div className="db-toolbar">
          <div className="db-search">
            <span aria-hidden="true">⌕</span>
            <input
              ref={searchRef}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={t.searchPlaceholder}
              aria-label={t.searchPlaceholder}
            />
          </div>
          <select
            className="db-filter"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            aria-label={t.filterStatus}
          >
            <option value="all">{t.allStatuses}</option>
            {['draft', 'processing', 'needs_review', 'conflicts_found', 'cleared'].map((value) => (
              <option value={value} key={value}>
                {t[value]}
              </option>
            ))}
          </select>
        </div>

        {error && (
          <ErrorState
            title={t.errorTitle}
            message={error}
            retryLabel={t.retry}
            onRetry={() => setReloadKey((key) => key + 1)}
          />
        )}

        {!error && loading && items.length === 0 && <SkeletonRows rows={5} />}

        {!error && !loading && showEmpty && (
          <EmptyState
            title={t.emptyTitle}
            text={t.emptyText}
            action={
              <button className="db-btn db-btn-primary" onClick={() => setShowNew(true)}>
                {t.newCase}
              </button>
            }
          />
        )}

        {!error && items.length > 0 && (
          <>
            <div className="db-table-card">
              <CaseTable cases={items} t={t} lang={lang} onOpen={openCase} />
            </div>

            <div className="db-pager">
              <span>
                {t.showing} {items.length} {t.of} {total} {t.cases}
              </span>
              {canLoadMore && (
                <button className="db-btn" onClick={loadMore} disabled={loading}>
                  {loading ? t.loading : t.loadMore}
                </button>
              )}
            </div>
          </>
        )}
      </main>

      {showNew && (
        <NewCaseDialog t={t} onSubmit={handleCreate} onClose={() => setShowNew(false)} />
      )}
    </div>
  );
}
