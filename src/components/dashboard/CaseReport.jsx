import React, { useEffect, useMemo, useState } from 'react';
import StatusBadge from './StatusBadge.jsx';
import SeverityBadge from './SeverityBadge.jsx';
import IgnoredHarmless from './IgnoredHarmless.jsx';
import { EmptyState } from './StateBlocks.jsx';
import { formatDate } from '../../i18n/dashboardText.js';

const SEVERITIES = ['HIGH', 'MEDIUM', 'LOW'];
const DECISIONS = ['pending', 'accepted', 'dismissed'];

function prettyField(field) {
  if (!field) return '—';
  const spaced = String(field).replace(/_/g, ' ').toLowerCase();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/**
 * Case report rendered below the existing document analysis page.
 *
 * @param {object}   caseItem    the persisted case (notes, status, decisions)
 * @param {object|null} analysis the live BundleDetectionResult from the
 *                               existing analysis page, or null before it runs
 */
export default function CaseReport({
  caseItem,
  analysis,
  t,
  lang,
  onDecision,
  onStatusChange,
  onNotesSave,
  onBack,
}) {
  const [notes, setNotes] = useState(caseItem?.notes || '');
  const [savingNotes, setSavingNotes] = useState(false);
  const [clearing, setClearing] = useState(false);

  useEffect(() => {
    setNotes(caseItem?.notes || '');
  }, [caseItem?.id, caseItem?.notes]);

  // Conflict rows come from the live analysis when it has run, otherwise from
  // the findings already stored on the case.
  const conflictRows = useMemo(() => {
    if (analysis) {
      // Index over the FULL array first, then filter. The analysis page builds
      // ids as `${field}-${index}` across all findings, so filtering first
      // would shift the indices and break decision keys.
      return analysis.findings
        .map((item, index) => ({ item, rowId: item.id || `${item.field}-${index}` }))
        .filter(({ item }) => item.decision !== 'harmless_variant')
        .map(({ item, rowId }) => {
          const evidence = item.evidence || [];
          return {
            id: rowId,
            field: item.field,
            severity: (item.severity || 'NONE').toUpperCase(),
            values: evidence.map((entry) => ({
              document: entry.document_type,
              value: entry.raw_value || entry.normalized_value || '—',
            })),
            location: evidence[0]
              ? { document: evidence[0].document_type, field: prettyField(item.field) }
              : { document: '—', field: prettyField(item.field) },
            explanation: item.reason || item.recommended_action || '',
          };
        });
    }

    return (caseItem?.findings || []).map((item) => ({
      ...item,
      severity: (item.severity || 'NONE').toUpperCase(),
    }));
  }, [analysis, caseItem]);

  const decisionFor = (row) => caseItem?.decisions?.[row.id] || 'pending';

  // Harmless variations: the backend's harmless_variant findings plus any
  // ignored items already recorded on the case, de-duplicated.
  const ignoredItems = useMemo(() => {
    const fromCase = caseItem?.ignored || [];
    const fromAnalysis = analysis
      ? analysis.findings
          .filter((item) => item.decision === 'harmless_variant')
          .map((item, index) => ({
            id: `analysis-${index}`,
            field: item.field,
            values: (item.evidence || [])
              .map((entry) => entry.raw_value || entry.normalized_value)
              .filter(Boolean),
            reason: item.reason || '',
          }))
      : [];

    const seen = new Set();
    return [...fromCase, ...fromAnalysis].filter((item) => {
      const key = `${item.field}|${(item.values || []).join('|')}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [analysis, caseItem]);

  const severityCounts = useMemo(() => {
    const counts = { HIGH: 0, MEDIUM: 0, LOW: 0 };
    conflictRows.forEach((row) => {
      if (counts[row.severity] !== undefined) counts[row.severity] += 1;
    });
    return counts;
  }, [conflictRows]);

  const pendingHigh = conflictRows.filter(
    (row) => row.severity === 'HIGH' && decisionFor(row) === 'pending'
  );

  const alreadyCleared = caseItem?.status === 'cleared';
  const canClear = pendingHigh.length === 0 && !alreadyCleared;
  const documentsCompared = analysis ? analysis.documents_processed : caseItem?.documentCount || 0;
  const hasAnalysis = Boolean(analysis) || (caseItem?.findings || []).length > 0;

  const saveNotes = async () => {
    setSavingNotes(true);
    try {
      await onNotesSave(notes);
    } finally {
      setSavingNotes(false);
    }
  };

  const markCleared = async () => {
    if (!canClear) return;
    setClearing(true);
    try {
      await onStatusChange('cleared');
    } finally {
      setClearing(false);
    }
  };

  return (
    <section className="db-report" aria-label={t.caseReport}>
      <header className="db-report-head">
        <div>
          <button className="db-link" onClick={onBack}>
            ← {t.backToDashboard}
          </button>
          <h2>{t.caseReport}</h2>
        </div>
        <button className="db-btn" onClick={() => window.print()}>
          ↓ {t.downloadReport}
        </button>
      </header>

      {/* a) Summary */}
      <div className="db-report-summary">
        <div className="db-sum-item">
          <small>{t.caseId}</small>
          <b>{caseItem?.id}</b>
        </div>
        <div className="db-sum-item">
          <small>{t.applicant}</small>
          <b>{caseItem?.applicantName}</b>
        </div>
        <div className="db-sum-item">
          <small>{t.applicationType}</small>
          <b>{caseItem?.applicationType}</b>
        </div>
        <div className="db-sum-item">
          <small>{t.created}</small>
          <b>{formatDate(caseItem?.createdAt, lang)}</b>
        </div>
        <div className="db-sum-item">
          <small>{t.documentsCompared}</small>
          <b>{documentsCompared}</b>
        </div>
        <div className="db-sum-item">
          <small>{t.harmlessIgnored}</small>
          <b>{ignoredItems.length}</b>
        </div>
        <div className="db-sum-item">
          <small>{t.overallStatus}</small>
          <b>
            <StatusBadge status={caseItem?.status} label={t[caseItem?.status]} />
          </b>
        </div>
      </div>

      <div className="db-severity-row">
        <span className="db-severity-title">{t.conflicts}</span>
        {SEVERITIES.map((severity) => (
          <span className="db-severity-chip" key={severity}>
            <SeverityBadge severity={severity} label={t[severity.toLowerCase()]} />
            <b>{severityCounts[severity]}</b>
          </span>
        ))}
      </div>

      {/* b) Findings table */}
      <div className="db-report-block">
        <h3>{t.findingsTable}</h3>

        {!hasAnalysis ? (
          <EmptyState title={t.noFindingsTitle} text={t.noFindingsText} />
        ) : conflictRows.length === 0 ? (
          <EmptyState title={t.noFindingsTitle} text={t.noneIgnored} />
        ) : (
          <div className="db-table-wrap">
            <table className="db-table db-report-table">
              <thead>
                <tr>
                  <th scope="col">{t.field}</th>
                  <th scope="col">{t.values}</th>
                  <th scope="col">{t.severity}</th>
                  <th scope="col">{t.location}</th>
                  <th scope="col">{t.explanation}</th>
                  <th scope="col">{t.decision}</th>
                </tr>
              </thead>
              <tbody>
                {conflictRows.map((row) => (
                  <tr key={row.id}>
                    <td className="db-cell-name">{prettyField(row.field)}</td>
                    <td>
                      <div className="db-value-pair">
                        {row.values.map((entry, index) => (
                          <span key={`${entry.document}-${index}`}>
                            <small>{entry.document}</small>
                            <b>{entry.value}</b>
                          </span>
                        ))}
                      </div>
                    </td>
                    <td>
                      <SeverityBadge severity={row.severity} label={t[row.severity.toLowerCase()]} />
                    </td>
                    <td>
                      <span className="db-location">
                        {row.location.document}
                        <small>{row.location.field}</small>
                      </span>
                    </td>
                    <td className="db-explanation">{row.explanation}</td>
                    <td>
                      <select
                        className={`db-decision-select db-decision-${decisionFor(row)}`}
                        aria-label={`${t.decision}: ${prettyField(row.field)}`}
                        value={decisionFor(row)}
                        onChange={(event) => onDecision(row.id, event.target.value)}
                      >
                        {DECISIONS.map((decision) => (
                          <option value={decision} key={decision}>
                            {t[`decision${decision.charAt(0).toUpperCase()}${decision.slice(1)}`]}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* c) Ignored as harmless */}
      <IgnoredHarmless items={ignoredItems} t={t} />

      {/* d) Reviewer notes */}
      <div className="db-report-block db-notes">
        <h3>{t.notesTitle}</h3>
        <textarea
          rows={4}
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          placeholder={t.notesPlaceholder}
          aria-label={t.notesTitle}
        />
        <div className="db-notes-actions">
          <button
            className="db-btn db-btn-primary"
            onClick={saveNotes}
            disabled={savingNotes || notes === (caseItem?.notes || '')}
          >
            {savingNotes ? t.saving : t.saveNotes}
          </button>
        </div>
      </div>

      {/* e) Actions */}
      <div className="db-report-actions">
        <button
          className="db-btn db-btn-primary"
          onClick={markCleared}
          disabled={!canClear || clearing}
          title={!canClear ? t.blockedCleared : undefined}
        >
          {alreadyCleared ? t.alreadyCleared : t.markCleared}
        </button>
        {!canClear && !alreadyCleared && (
          <span className="db-hint" role="status">
            {t.blockedCleared}
          </span>
        )}
        <button className="db-btn" onClick={() => window.print()}>
          ↓ {t.downloadReport}
        </button>
        <button className="db-btn" onClick={onBack}>
          ← {t.backToDashboard}
        </button>
      </div>
    </section>
  );
}
