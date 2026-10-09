import React, { useState } from 'react';

function prettyField(field) {
  if (!field) return '—';
  const spaced = String(field).replace(/_/g, ' ').toLowerCase();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

// Collapsed list of harmless variations the detector matched and ignored, so
// reviewers can see that nothing was hidden from them.
export default function IgnoredHarmless({ items, t }) {
  const [open, setOpen] = useState(false);
  const list = items || [];

  return (
    <section className="db-ignored">
      <button
        type="button"
        className="db-ignored-toggle"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <span>
          {t.ignoredTitle} <em>{list.length}</em>
          <small>{t.ignoredNote}</small>
        </span>
        <b aria-hidden="true">{open ? '⌃' : '⌄'}</b>
      </button>

      {/* Always rendered so the print stylesheet can expand it — reviewers
          must never see a PDF with items hidden. */}
      <div className={`db-ignored-body${open ? ' open' : ''}`}>
        {list.length ? (
          list.map((item) => (
            <p key={item.id}>
              <b>{prettyField(item.field)}</b>
              <span>
                {item.values[0]} <i>vs</i> {item.values[1]}
              </span>
              <em>— {item.reason}</em>
            </p>
          ))
        ) : (
          <p className="db-ignored-empty">{t.noneIgnored}</p>
        )}
      </div>
    </section>
  );
}
