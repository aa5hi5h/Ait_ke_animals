import React from 'react';

// Severity badge: colour AND text label, never colour alone.
const TONE = { HIGH: 'danger', MEDIUM: 'warn', LOW: 'info', NONE: 'neutral' };

export default function SeverityBadge({ severity, label }) {
  const value = (severity || 'NONE').toUpperCase();
  return (
    <span className={`db-badge db-sev-${TONE[value] || 'neutral'}`}>
      <i aria-hidden="true" />
      {label || value}
    </span>
  );
}
