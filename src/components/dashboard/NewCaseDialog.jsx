import React, { useState } from 'react';
import { APPLICATION_TYPES } from '../../mock/cases.js';

// New case form. Used as a modal from the dashboard and as a page at
// /cases/new (renderModal={false}).
export default function NewCaseDialog({ t, onSubmit, onClose, renderModal = true }) {
  const [applicantName, setApplicantName] = useState('');
  const [applicationType, setApplicationType] = useState('');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    if (!applicantName.trim() || !applicationType) {
      setError(t.required);
      return;
    }

    setPending(true);
    setError('');
    try {
      await onSubmit({ applicantName, applicationType, notes });
    } catch (requestError) {
      setError(requestError.message || t.required);
      setPending(false);
    }
  };

  const form = (
    <form className="db-form" onSubmit={submit}>
      <div className="db-field">
        <label htmlFor="db-applicant">{t.applicantLabel}</label>
        <input
          id="db-applicant"
          value={applicantName}
          onChange={(event) => setApplicantName(event.target.value)}
          placeholder={t.applicantPlaceholder}
          autoFocus
          required
        />
      </div>

      <div className="db-field">
        <label htmlFor="db-type">{t.typeLabel}</label>
        <select
          id="db-type"
          value={applicationType}
          onChange={(event) => setApplicationType(event.target.value)}
          required
        >
          <option value="">{t.typePlaceholder}</option>
          {APPLICATION_TYPES.map((type) => (
            <option value={type} key={type}>
              {type}
            </option>
          ))}
        </select>
      </div>

      <div className="db-field">
        <label htmlFor="db-notes">{t.notesLabel}</label>
        <textarea
          id="db-notes"
          rows={3}
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          placeholder={t.notesPlaceholder}
        />
      </div>

      {error && (
        <p className="db-form-error" role="alert">
          {error}
        </p>
      )}

      <div className="db-form-actions">
        {onClose && (
          <button type="button" className="db-btn" onClick={onClose} disabled={pending}>
            {t.cancel}
          </button>
        )}
        <button type="submit" className="db-btn db-btn-primary" disabled={pending}>
          {pending ? t.creating : t.create}
        </button>
      </div>
    </form>
  );

  if (!renderModal) {
    return (
      <div className="db-newcase-page">
        <h2>{t.newCaseTitle}</h2>
        <p>{t.newCaseText}</p>
        {form}
      </div>
    );
  }

  return (
    <div className="db-modal-backdrop" onClick={() => !pending && onClose?.()}>
      <section
        className="db-modal"
        role="dialog"
        aria-modal="true"
        aria-label={t.newCaseTitle}
        onClick={(event) => event.stopPropagation()}
      >
        <button
          className="db-modal-close"
          onClick={() => onClose()}
          disabled={pending}
          aria-label={t.cancel}
        >
          ×
        </button>
        <h2>{t.newCaseTitle}</h2>
        <p>{t.newCaseText}</p>
        {form}
      </section>
    </div>
  );
}
