import React from 'react';
import StatusBadge from './StatusBadge.jsx';
import { formatDate } from '../../i18n/dashboardText.js';

// Case table on desktop, cards on mobile. Rows are sorted newest first by
// the caller (listCases). Selecting a row opens /cases/:caseId.
export default function CaseTable({ cases, t, lang, onOpen }) {
  const columns = [
    t.caseId,
    t.applicant,
    t.applicationType,
    t.documents,
    t.created,
    t.updated,
    t.status,
    t.conflicts,
  ];

  return (
    <>
      <div className="db-table-wrap">
        <table className="db-table">
          <thead>
            <tr>
              {columns.map((label) => (
                <th key={label} scope="col">
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {cases.map((item) => (
              <tr
                key={item.id}
                tabIndex={0}
                role="link"
                aria-label={`${t.openCase}: ${item.id} ${item.applicantName}`}
                onClick={() => onOpen(item.id)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    onOpen(item.id);
                  }
                }}
              >
                <td className="db-cell-id">{item.id}</td>
                <td className="db-cell-name">{item.applicantName}</td>
                <td>{item.applicationType}</td>
                <td>{item.documentCount}</td>
                <td>{formatDate(item.createdAt, lang)}</td>
                <td>{formatDate(item.updatedAt, lang)}</td>
                <td>
                  <StatusBadge status={item.status} label={t[item.status]} />
                </td>
                <td className="db-cell-count">{item.findings.length}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile cards */}
      <div className="db-cards">
        {cases.map((item) => (
          <button
            className="db-case-card"
            key={item.id}
            onClick={() => onOpen(item.id)}
            aria-label={`${t.openCase}: ${item.id} ${item.applicantName}`}
          >
            <div className="db-case-card-top">
              <b>{item.id}</b>
              <StatusBadge status={item.status} label={t[item.status]} />
            </div>
            <p className="db-case-card-name">{item.applicantName}</p>
            <div className="db-case-card-meta">
              <span>{item.applicationType}</span>
              <span>
                {item.documentCount} {t.documents}
              </span>
              <span>
                {item.findings.length} {t.conflicts}
              </span>
            </div>
            <small>{formatDate(item.updatedAt, lang)}</small>
          </button>
        ))}
      </div>
    </>
  );
}
