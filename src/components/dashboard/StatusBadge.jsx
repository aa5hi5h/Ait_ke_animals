import React from 'react';

// Status badge: colour AND text label, never colour alone.
const TONE = {
  draft: 'neutral',
  processing: 'info',
  needs_review: 'warn',
  conflicts_found: 'danger',
  cleared: 'success',
};

export default function StatusBadge({ status, label }) {
  return (
    <span className={`db-badge db-status-${TONE[status] || 'neutral'}`}>
      <i aria-hidden="true" />
      {label || status}
    </span>
  );
}
