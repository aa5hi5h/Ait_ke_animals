import React from 'react';
import { statusCounts } from '../../api/cases.js';

// Four summary cards. Values come from listCases().counts (the whole case
// list) and fall back to computing from whatever list is in hand — nothing
// here is hardcoded.
export default function SummaryCards({ cases, counts, t }) {
  const derived = counts || statusCounts(cases || []);

  const cards = [
    { key: 'total', label: t.totalCases, value: derived.total, tone: 'total' },
    { key: 'needs', label: t.needsReviewCard, value: derived.needsReview, tone: 'warn' },
    { key: 'conflicts', label: t.conflictsFoundCard, value: derived.conflictsFound, tone: 'danger' },
    { key: 'cleared', label: t.clearedCard, value: derived.cleared, tone: 'success' },
  ];

  return (
    <div className="db-summary">
      {cards.map((card) => (
        <div className={`db-summary-card db-tone-${card.tone}`} key={card.key}>
          <span className="db-summary-label">{card.label}</span>
          <strong className="db-summary-value">{card.value}</strong>
          <span className="db-summary-bar" aria-hidden="true" />
        </div>
      ))}
    </div>
  );
}
