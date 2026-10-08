import React, { useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const supportedFields = ['Name', 'DOB', 'Father/Mother name', 'Address', 'Income'];
const initialFindings = [
  { id: 'f1', field: 'DOB', severity: 'HIGH', status: 'pending', docs: ['PAN card', 'Aadhaar card'], values: ['2001-03-12', '2001-08-12'], confidence: 98, explanation: 'DOB on PAN card differs from Aadhaar card.', source: 'PAN card · Page 1 · bbox [40,180,420,220]' },
  { id: 'f2', field: 'Address', severity: 'MEDIUM', status: 'pending', docs: ['Aadhaar card', 'Application form'], values: ['14, Lake View Road, Pune', '14 Lakeview Road, Pune'], confidence: 91, explanation: 'The normalized address values differ. Verify the house number and locality.', source: 'Application form · Page 1 · bbox [60,300,400,340]' },
  { id: 'f3', field: 'Name', severity: 'LOW', status: 'accepted', docs: ['Aadhaar card', 'Driving license'], values: ['PRIYA SHARMA', 'Priya Kumari Sharma'], confidence: 96, explanation: 'Name variation was retained as a non-conflict after normalization.', source: 'Driving license · Page 1 · bbox [40,180,420,220]' }
];
const documents = [
  { name: 'Aadhaar card', short: 'Aadhaar', pages: 1, confidence: '99.2%', fields: 'Name · DOB · Parent name · Address' },
  { name: 'PAN card', short: 'PAN', pages: 1, confidence: '98.5%', fields: 'Name · DOB · Parent name' },
  { name: 'Application form', short: 'Application', pages: 2, confidence: '97.8%', fields: 'Name · DOB · Address · Income' },
  { name: 'Income certificate', short: 'Income', pages: 1, confidence: '96.4%', fields: 'Name · Income · Address' },
  { name: 'Driving license', short: 'Driving license', pages: 1, confidence: '94.6%', fields: 'Name · DOB · Address' }
];

function App() {
  const [active, setActive] = useState('Documents Detail');
  const [tab, setTab] = useState('Overview');
  const [findings, setFindings] = useState(initialFindings);
  const [selected, setSelected] = useState('f1');
  const [query, setQuery] = useState('');
  const [showUpload, setShowUpload] = useState(false);
  const [showEvidence, setShowEvidence] = useState(false);
  const [showVerify, setShowVerify] = useState(false);
  const [ocrValue, setOcrValue] = useState('14 Aug 1996');
  const [toast, setToast] = useState('');
  const current = findings.find(f => f.id === selected) || findings[0];
  const visibleFindings = useMemo(() => findings.filter(f => `${f.field} ${f.docs.join(' ')} ${f.explanation}`.toLowerCase().includes(query.toLowerCase())), [findings, query]);
  const notify = (message) => { setToast(message); window.setTimeout(() => setToast(''), 2600); };
  const updateFinding = (status) => { setFindings(all => all.map(f => f.id === current.id ? { ...f, status } : f)); notify(`Finding marked ${status}.`); };

  return <div className="shell">
    <aside className="sidebar">
      <div className="profile"><div className="profile-photo">PS</div><div><b>Priya Sharma</b><small>Citizen bundle</small></div><span>⌄</span></div>
      <div className="side-rule" />
      <nav className="primary-nav">
        {['Dashboard', 'Document Management', 'Document Reports'].map((item, i) => <button key={item} className={`side-link ${active === item ? 'active' : ''}`} onClick={() => setActive(item)}><span className="side-icon">{['⌂', '▤', '▥'][i]}</span>{item}{item !== 'Dashboard' && <span className="side-caret">⌄</span>}</button>)}
      </nav>
      <div className="side-label">DOCUMENTS</div>
      {['Documents Detail', 'Personal Documents', 'User Documents', 'Customer Documents', 'Contracts', 'Receipts'].map((item, i) => <button key={item} className={`side-link nested ${active === item ? 'active' : ''}`} onClick={() => setActive(item)}><span className="side-icon">{i === 0 ? '▣' : '·'}</span>{item}</button>)}
      <div className="sidebar-bottom"><button className="bottom-link">? <span>Help Started</span></button><button className="bottom-link">＋ <span>Add New Folder</span></button></div>
    </aside>
    <main className="main">
      <header className="topbar"><div className="breadcrumbs"><span>Workspace</span><b>/</b><span>Documents</span><b>/</b><strong>Documents Details</strong></div><div className="header-actions"><button className="header-icon">◐</button><button className="header-icon">◌</button><div className="user-mini">AK</div></div></header>
      <div className="page">
        <div className="page-title"><div><h1>Documents Details <span className="info">?</span></h1><p>Review supported citizen documents, extracted fields and contradictions in one bundle.</p></div><div className="title-actions"><button className="primary-outline" onClick={() => setShowUpload(true)}>＋ Add documents</button></div></div>
        <div className="tabs"><button className={tab === 'Overview' ? 'selected' : ''} onClick={() => setTab('Overview')}>Overview</button><button className={tab === 'Add Document' ? 'selected' : ''} onClick={() => { setTab('Add Document'); setShowUpload(true); }}>＋ Add Document</button></div>
        {tab === 'Overview' ? <>
          <div className="toolbar"><div className="search"><span>⌕</span><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search for document or finding..." /></div><button className="filter-button">≡ &nbsp; Filters</button><button className="attachment-button">⌕ &nbsp; Attachment</button></div>
          <div className="filter-row"><Filter text="All document types" /><Filter text="Field" /><Filter text="Severity" /><Filter text="Review status" /><Filter text="Source document" /></div>
          <div className="dropzone"><span className="drop-icon">▧</span><b>Drop your documents here, or select</b><button onClick={() => setShowUpload(true)}>click to browse</button><small>PDF, PNG, JPG up to 20 MB each · five supported document types</small></div>
          <section className="table-card"><div className="table-heading"><div><h2>Document bundle <span>{documents.length}</span></h2><p>APP-24081 · only supported fields are extracted from this citizen bundle</p></div><div className="bundle-status"><i /> Analysis complete</div></div><div className="document-table"><div className="table-row table-header"><span>Document name</span><span>Document type</span><span>Pages</span><span>Extracted fields</span><span>OCR status</span><span>Operation</span></div>{documents.map((doc, i) => <div className="table-row" key={doc.name}><span className="document-name"><i className={`doc-symbol symbol-${i % 3}`}>▤</i><b>{doc.name}</b></span><span><em className="type-tag">{doc.short}</em></span><span>{doc.pages}</span><span className="field-text">{doc.fields}</span><span><em className="complete-tag">✓ Complete</em><small>{doc.confidence} confidence</small></span><span className="row-actions"><button onClick={() => setShowEvidence(true)}>↗</button><button onClick={() => setShowVerify(true)}>◉</button><button>▧</button></span></div>)}</div><div className="table-footer"><span>1–{documents.length} of {documents.length} documents</span><span>Page <b>1</b> of 1　‹　›</span></div></section>
          <section className="summary-card"><div className="summary-heading"><div><span className="summary-kicker">BUNDLE RESULT</span><h2>Citizen bundle summary</h2><p>One complete result for this document bundle.</p></div><span className="summary-status">Analysis complete</span></div><div className="summary-stats"><div><small>Documents processed</small><b>{documents.length}</b></div><div><small>Conflicts</small><b>{findings.filter(f => f.severity !== 'LOW').length}</b></div><div><small>Harmless variants</small><b>{findings.filter(f => f.severity === 'LOW').length}</b></div><div><small>Needs review</small><b>{findings.filter(f => f.status === 'pending').length}</b></div><div><small>Highest severity</small><b className="summary-high">{findings.some(f => f.severity === 'HIGH') ? 'HIGH' : 'NONE'}</b></div></div></section><div className="lower-grid"><section className="findings-card"><div className="card-heading"><div><h2>Findings requiring review <span>{findings.filter(f => f.status === 'pending').length}</span></h2><p>Compare only Name, DOB, parent name, address and income.</p></div><button className="link-button">View all findings →</button></div>{visibleFindings.map(f => <button key={f.id} className={`finding-line ${selected === f.id ? 'selected' : ''}`} onClick={() => setSelected(f.id)}><span className={`severity-mark ${f.severity.toLowerCase()}`} /><span className="finding-field"><b>{f.field}</b><small>{f.docs[0]} vs {f.docs[1]}</small></span><span className="finding-values">{f.values[0]} <i>→</i> {f.values[1]}</span><em className={`status-tag ${f.status}`}>{f.status}</em><span>›</span></button>)}</section><aside className="review-card"><div className="card-heading"><div><h2>Selected finding</h2><p>Backend explanation and review action</p></div></div><span className={`severity-label ${current.severity.toLowerCase()}`}>{current.severity}</span><h3>{current.field}</h3><p className="explanation">{current.explanation}</p><div className="compare-box"><Source label={current.docs[0]} value={current.values[0]} /><Source label={current.docs[1]} value={current.values[1]} /></div><div className="review-card-actions"><button onClick={() => setShowEvidence(true)}>View evidence</button><button onClick={() => setShowVerify(true)}>Verify OCR</button></div>{current.status === 'pending' ? <div className="decision"><button onClick={() => updateFinding('dismissed')}>Dismiss</button><button onClick={() => updateFinding('accepted')}>Accept finding</button></div> : <div className="resolved">✓ {current.status}</div>}</aside></div>
          <section className="fields-card"><div className="card-heading"><div><h2>Fields compared</h2><p>Normalization and comparison are handled by the backend.</p></div></div><div className="field-list">{supportedFields.map(field => <span key={field}>✓ {field}</span>)}</div></section>
        </> : <div className="empty-tab"><div className="empty-icon">＋</div><h2>Add documents to this bundle</h2><p>Upload Aadhaar card, PAN card, application form, income certificate or driving license.</p><button className="primary-button" onClick={() => setShowUpload(true)}>Choose documents</button></div>}
      </div>
    </main>
    {showUpload && <div className="modal-backdrop" onClick={() => setShowUpload(false)}><div className="upload-modal" onClick={e => e.stopPropagation()}><button className="modal-close" onClick={() => setShowUpload(false)}>×</button><div className="modal-kicker">NEW DOCUMENT BUNDLE</div><h2>Upload documents</h2><p>Add multiple files for one citizen. The backend will classify, OCR and analyze the bundle.</p><div className="modal-drop"><b>Drop files here</b><label>Browse from your computer<input type="file" multiple accept=".pdf,.png,.jpg,.jpeg" /></label><small>PDF, PNG, JPG up to 20 MB each</small></div><button className="primary-button full" onClick={() => { setShowUpload(false); notify('Bundle upload queued for analysis.'); }}>Upload and analyze</button></div></div>}
    {showEvidence && <div className="modal-backdrop" onClick={() => setShowEvidence(false)}><div className="evidence-modal" onClick={e => e.stopPropagation()}><button className="modal-close" onClick={() => setShowEvidence(false)}>×</button><div className="modal-kicker">EVIDENCE VIEW · {current.field}</div><h2>Source evidence</h2><p>Highlighted boxes show the OCR source locations returned by the backend.</p><div className="evidence-grid"><Evidence label={current.docs[0]} value={current.values[0]} bbox="40,180,420,220" /><Evidence label={current.docs[1]} value={current.values[1]} bbox="60,300,400,340" /></div></div></div>}
    {showVerify && <div className="modal-backdrop" onClick={() => setShowVerify(false)}><div className="verify-modal" onClick={e => e.stopPropagation()}><button className="modal-close" onClick={() => setShowVerify(false)}>×</button><div className="modal-kicker">VERIFY OCR · NEEDS REVIEW</div><h2>Confirm extracted value</h2><p>Save a corrected value through the backend field update endpoint.</p><label>Extracted {current.field} from {current.docs[1]}</label><input value={ocrValue} onChange={e => setOcrValue(e.target.value)} /><div className="modal-actions"><button onClick={() => setShowVerify(false)}>Cancel</button><button className="primary-button" onClick={() => { setShowVerify(false); notify('OCR value saved for review.'); }}>Save value</button></div></div></div>}
    {toast && <div className="toast">✓ {toast}</div>}
  </div>;
}

function Filter({ text }) { return <button className="filter-select">{text}<span>⌄</span></button>; }
function Source({ label, value }) { return <div className="source"><span>▤ {label}</span><b>{value}</b></div>; }
function Evidence({ label, value, bbox }) { return <div className="evidence-doc"><div><b>{label}</b><small>Page 1</small></div><div className="paper"><span className="paper-line" /><span className="paper-line short" /><span className="paper-line" /><span className="bbox">{value}</span></div><small className="bbox-text">bbox: [{bbox}]</small></div>; }

createRoot(document.getElementById('root')).render(<App />);

