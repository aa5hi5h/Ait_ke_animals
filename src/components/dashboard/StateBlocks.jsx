import React from 'react';

export function SkeletonRows({ rows = 5 }) {
  return (
    <div className="db-skeleton-card" aria-hidden="true">
      {Array.from({ length: rows }).map((_, index) => (
        <div className="db-skeleton-row" key={index}>
          <span className="db-sk db-sk-lg" />
          <span className="db-sk db-sk-md" />
          <span className="db-sk db-sk-sm" />
          <span className="db-sk db-sk-md" />
        </div>
      ))}
    </div>
  );
}

export function EmptyState({ title, text, action }) {
  return (
    <div className="db-state">
      <div className="db-state-icon" aria-hidden="true">▤</div>
      <h3>{title}</h3>
      <p>{text}</p>
      {action}
    </div>
  );
}

export function ErrorState({ title, message, onRetry, retryLabel }) {
  return (
    <div className="db-state db-state-error" role="alert">
      <div className="db-state-icon" aria-hidden="true">!</div>
      <h3>{title}</h3>
      <p>{message}</p>
      <button className="db-btn db-btn-primary" onClick={onRetry}>
        {retryLabel}
      </button>
    </div>
  );
}
