import React, { useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

// Demo response shaped like the backend Finding JSON. Only supported fields are shown.
const initialFindings = [
  { id: 'f1', field: 'DOB', type: 'Direct conflict', severity: 'HIGH', status: 'pending', docs: ['PAN card', 'Aadhaar card'], values: ['2001-03-12', '2001-08-12'], confidence: 98, detail: 'DOB on PAN card differs from Aadhaar card.', source: 'PAN card · Page 1 · bbox [40,180,420,220]', color: '#e76f51' },
  { id: 'f2', field: 'Address', type: 'Possible conflict', severity: 'MEDIUM', status: 'pending', docs: ['Aadhaar card', 'Application form'], values: ['14, Lake View Road, Pune', '14 Lakeview Road, Pune'], confidence: 91, detail: 'The normalized address values differ. Verify the house number and locality.', source: 'Application form · Page 1 · bbox [60,300,400,340]', color: '#e5a83b' },
  { id: 'f3', field: 'Name', type: 'Harmless variant', severity: 'LOW', status: 'accepted', docs: ['Aadhaar card', 'Driving license'], values: ['PRIYA SHARMA', 'Priya Kumari Sharma'], confidence: 96, detail: 'Name variation was retained as a non-conflict after normalization.', source: 'Driving license · Page 1 · bbox [40,180,420,220]', color: '#6fcf97' }
];

const documents = [
  { name: 'Aadhaar card', kind: 'Supported document', pages: 1, confidence: '99.2%', status: 'Processed', icon: '▧', tone: 'blue', fields: 'Name · DOB · Parent name · Address' },
  { name: 'PAN card', kind: 'Supported document', pages: 1, confidence: '98.5%', status: 'Processed', icon: '▤', tone: 'purple', fields: 'Name · DOB · Parent name' },
  { name: 'Application form', kind: 'Supported document', pages: 2, confidence: '97.8%', status: 'Processed', icon: '▥', tone: 'orange', fields: 'Name · DOB · Address · Income' },
  { name: 'Income certificate', kind: 'Supported document', pages: 1, confidence: '96.4%', status: 'Processed', icon: '▤', tone: 'purple', fields: 'Name · Income · Address' },
  { name: 'Driving license', kind: 'Supported document', pages: 1, confidence: '94.6%', status: 'Processed', icon: '▥', tone: 'orange', fields: 'Name · DOB · Address' }
];

const supportedFields = ['Name', 'DOB', 'Father/Mother name', 'Address', 'Income'];

function Icon({ children }) { return <span className="icon" aria-hidden="true">{children}</span>; }

function App() {
  const [active, setActive] = useState('Overview');
  const [findings, setFindings] = useState(initialFindings);
  const [selected, setSelected] = useState(1);
  const [showUpload, setShowUpload] = useState(false);
  const [showEvidence, setShowEvidence] = useState(false);
  const [showVerify, setShowVerify] = useState(false);
  const [ocrValue, setOcrValue] = useState('14 Aug 1996');
  const [query, setQuery] = useState('');
  const [toast, setToast] = useState('');

  const visibleFindings = useMemo(() => findings.filter(f => `${f.field} ${f.type} ${f.docs.join(' ')}`.toLowerCase().includes(query.toLowerCase())), [findings, query]);
  const current = findings.find(f => f.id === selected) || findings[0];
  const actOnFinding = (status) => {
    setFindings(all => all.map(f => f.id === current.id ? { ...f, status } : f));
    setToast(status === 'accepted' ? 'Finding accepted and added to the review record.' : 'Finding dismissed.');
    window.setTimeout(() => setToast(''), 2800);
  };

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">N</div><div><strong>nazar</strong><span>DOCUMENT INTELLIGENCE</span></div></div>
      <div className="workspace-label">WORKSPACE</div>
      <div className="workspace"><div className="workspace-avatar">PS</div><div><b>Public Systems</b><small>Demo workspace</small></div><span className="chevron">⌄</span></div>
      <nav>
        {['Overview', 'Review queue', 'Documents'].map((item, i) => <button key={item} className={`nav-item ${active === item ? 'active' : ''}`} onClick={() => setActive(item)}><Icon>{['⌂', '◎', '▤'][i]}</Icon>{item}{item === 'Review queue' && <em>{findings.filter(x => x.status === 'pending').length}</em>}</button>)}
      </nav>
      <div className="workspace-label lower">TOOLS</div>
      <nav>
        <button className="nav-item"><Icon>⌁</Icon>Evaluation</button>
        <button className="nav-item"><Icon>⚙</Icon>Settings</button>
      </nav>
      <div className="sidebar-bottom"><div className="privacy"><span className="shield">✓</span><div><b>Synthetic data mode</b><small>No real citizen data</small></div><span className="toggle on"><i /></span></div><div className="user"><div className="user-avatar">AK</div><div><b>Arjun Kapoor</b><small>Reviewer</small></div><span className="more">•••</span></div></div>
    </aside>
    <main className="main">
      <header className="topbar"><div className="crumb"><span>Applications</span><b>/</b><strong>APP-24081</strong><span className="status-pill">In review</span></div><div className="top-actions"><button className="language">अ <span>EN</span>⌄</button><button className="help">?</button><div className="notification">♧<i /></div></div></header>
      <div className="content">
        <div className="page-heading"><div><div className="eyebrow">BUNDLE APP-24081 <span>•</span> UPDATED 12 MIN AGO</div><h1>Review document bundle</h1><p>Check extracted information and resolve differences before making a decision.</p></div><button className="outline-btn" onClick={() => setShowUpload(true)}><span>＋</span> Add documents</button></div>
        <section className="applicant-card"><div className="applicant-avatar">PS</div><div className="applicant-info"><h2>Priya Sharma</h2><p>One citizen bundle <span>•</span> Submitted 08 Feb 2024</p></div><div className="card-meta"><small>EXTRACTION STATUS</small><strong className="status-text">Complete</strong><div className="mini-bar"><i style={{width:'100%'}} /></div></div><div className="card-meta findings-meta"><small>FINDINGS</small><strong>{findings.filter(x => x.status === 'pending').length} <span>pending</span></strong><a onClick={() => setActive('Review queue')}>View findings →</a></div></section>
        <div className="metrics"><Metric label="Documents processed" value="5 / 5" note="All documents ready" icon="▤" tone="blue" /><Metric label="Fields extracted" value="25" note="Across 3 documents" icon="✣" tone="purple" /><Metric label="Conflicts detected" value="2" note="1 high · 1 medium" icon="!" tone="red" /><Metric label="Harmless variants" value="1" note="Automatically ignored" icon="✓" tone="green" /></div>
        <div className="section-head"><div><h2>Review findings <span className="count">{visibleFindings.length}</span></h2><p>Compare extracted fields across submitted documents.</p></div><div className="finding-tools"><div className="search"><span>⌕</span><input placeholder="Search findings" value={query} onChange={e => setQuery(e.target.value)} /></div><button className="filter">≡ <span>Filter</span></button></div></div>
        <div className="review-layout"><section className="findings-list">{visibleFindings.map(f => <button className={`finding-row ${selected === f.id ? 'selected' : ''}`} key={f.id} onClick={() => setSelected(f.id)}><div className={`severity-dot ${f.severity.toLowerCase()}`} /><div className="finding-main"><div className="finding-title"><strong>{f.field}</strong><span className={`severity-label ${f.severity.toLowerCase()}`}>{f.severity}</span>{f.status !== 'pending' && <span className="reviewed">✓ {f.status}</span>}</div><p>{f.docs[0]} <span>vs</span> {f.docs[1]}</p><div className="value-compare"><span>{f.values[0]}</span><b>→</b><span>{f.values[1]}</span></div></div><span className="row-arrow">›</span></button>)}</section><aside className="detail-panel"><div className="detail-top"><div><span className={`severity-label ${current.severity.toLowerCase()}`}>{current.severity}</span><h3>{current.field} finding</h3></div><button className="close-detail">×</button></div><p className="detail-copy">{current.detail}</p><div className="confidence"><span>OCR / matching confidence</span><b>{current.confidence}%</b><div className="confidence-line"><i style={{width:`${current.confidence}%`}} /></div></div><div className="source-block"><div className="source-heading"><b>Values found in documents</b><a onClick={() => setShowEvidence(true)}>View evidence ↗</a></div><Source label={current.docs[0]} value={current.values[0]} /><Source label={current.docs[1]} value={current.values[1]} /></div><div className="location"><span>⌖</span><div><b>Source location</b><small>{current.source} · bounding box available</small></div></div><div className="review-tools"><button className="verify-link" onClick={() => setShowVerify(true)}>Edit extracted value</button><button className="verify-link" onClick={() => setShowEvidence(true)}>Open evidence</button></div>{current.status === 'pending' ? <div className="decision"><button className="dismiss" onClick={() => actOnFinding('dismissed')}>Dismiss</button><button className="accept" onClick={() => actOnFinding('accepted')}>Accept finding</button></div> : <div className="resolved">✓ This finding was {current.status}</div>}</aside></div>
        <section className="supported-fields"><div className="section-head compact"><div><h2>Fields compared</h2><p>Only these normalized fields are extracted and compared across the bundle.</p></div></div><div className="field-chips">{supportedFields.map(field => <span key={field}>✓ {field}</span>)}</div></section><section className="documents-section"><div className="section-head compact"><div><h2>Submitted documents</h2><p>OCR and extraction status for the five supported document types.</p></div><button className="text-btn" onClick={() => setActive('Documents')}>View all documents →</button></div><div className="document-grid">{documents.map(d => <div className="document-card" key={d.name}><div className={`doc-icon ${d.tone}`}>{d.icon}</div><div className="doc-text"><b>{d.name}</b><small>{d.kind} <span>•</span> {d.pages} {d.pages === 1 ? 'page' : 'pages'}</small><small className="doc-fields">{d.fields}</small></div><div className="doc-status"><span>✓</span> {d.status}<small>{d.confidence} OCR confidence</small></div><button className="doc-more">•••</button></div>)}</div></section>
      </div>
    </main>
    {showUpload && <div className="modal-backdrop" onClick={() => setShowUpload(false)}><div className="upload-modal" onClick={e => e.stopPropagation()}><button className="modal-close" onClick={() => setShowUpload(false)}>×</button><div className="upload-symbol">↑</div><h2>Upload document bundle</h2><p>Add all documents for one citizen. The bundle will be classified, OCR-processed and analyzed together.</p><div className="dropzone"><b>Drop PDF or image files here</b><label className="browse-label">Browse files<input className="file-input" type="file" multiple accept=".pdf,.png,.jpg,.jpeg" /></label><small>PDF, PNG, JPG up to 20 MB each · multiple files supported</small></div><button className="accept full" onClick={() => { setShowUpload(false); setToast('Bundle uploaded — analysis has been queued.'); window.setTimeout(() => setToast(''), 2800); }}>Upload and analyze</button></div></div>}
    {showEvidence && <div className="modal-backdrop" onClick={() => setShowEvidence(false)}><div className="evidence-modal" onClick={e => e.stopPropagation()}><button className="modal-close" onClick={() => setShowEvidence(false)}>×</button><div className="modal-kicker">EVIDENCE VIEW · {current.field.toUpperCase()}</div><h2>Source evidence</h2><p>Highlighted boxes show the exact location returned by OCR for this finding.</p><div className="evidence-grid"><EvidenceDoc label={current.docs[0]} value={current.values[0]} bbox="40, 180, 420, 220" /><EvidenceDoc label={current.docs[1]} value={current.values[1]} bbox="60, 300, 400, 340" /></div></div></div>}
    {showVerify && <div className="modal-backdrop" onClick={() => setShowVerify(false)}><div className="verify-modal" onClick={e => e.stopPropagation()}><button className="modal-close" onClick={() => setShowVerify(false)}>×</button><div className="modal-kicker">VERIFY OCR · NEEDS REVIEW</div><h2>Confirm extracted value</h2><p>Correct the value if the scan was read incorrectly. The saved value will be sent to the field verification endpoint.</p><label className="verify-label">{current.field} · {current.docs[1]}</label><input className="verify-input" value={ocrValue} onChange={e => setOcrValue(e.target.value)} /><div className="verify-actions"><button className="dismiss" onClick={() => setShowVerify(false)}>Cancel</button><button className="accept" onClick={() => { setShowVerify(false); setToast('OCR value saved for review.'); window.setTimeout(() => setToast(''), 2800); }}>Save value</button></div></div></div>}
    {toast && <div className="toast">✓ {toast}</div>}
  </div>
}

function Metric({label,value,note,icon,tone}) { return <div className="metric"><div className={`metric-icon ${tone}`}>{icon}</div><div><small>{label}</small><strong>{value}</strong><span>{note}</span></div></div> }
function Source({label,value}) { return <div className="source"><div className="source-doc"><span>▧</span><b>{label}</b></div><div className="source-value">{value}</div></div> }
function EvidenceDoc({label,value,bbox}) { return <div className="evidence-doc"><div className="evidence-head"><b>{label}</b><span>Page 1</span></div><div className="document-preview"><div className="fake-lines"><i/><i/><i/><i/><i/><i/></div><div className="bbox"><span>{value}</span></div></div><small>bbox: [{bbox}]</small></div> }

createRoot(document.getElementById('root')).render(<App />);



