import { useCallback, useEffect, useState } from 'react';
import { api } from '../api.js';

const TOPICS = [
  'Politics, Governance, and Elections', 'Health and Medicine',
  'Economy, Finance, and Employment', 'Public Safety, Disaster, and Security',
  'Science, Technology, and Environment', 'Education and Social Issues',
  'Entertainment and Public Figures', 'Other and General',
];

const EMPTY_EVIDENCE = { source_url: '', publisher: '', rating: '', claim_match_status: 'unreviewed', notes: '' };

export default function Candidates() {
  const [rows, setRows] = useState([]);
  const [labels, setLabels] = useState({});
  const [metadata, setMetadata] = useState({});
  const [selected, setSelected] = useState(null);
  const [evidence, setEvidence] = useState([]);
  const [form, setForm] = useState(EMPTY_EVIDENCE);
  const [filters, setFilters] = useState({ topic: '', validation_status: '', evidence_status: '' });
  const [intake, setIntake] = useState({ topics: [], totals: {} });
  const [exporting, setExporting] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(() => Promise.all([
    api.get('/candidates', { params: Object.fromEntries(Object.entries(filters).filter(([, value]) => value)) }),
    api.get('/candidate-summary'),
  ]).then(([candidates, summary]) => {
    setRows(candidates.data.candidates);
    setIntake(summary.data);
  })
    .catch((reason) => setError(reason.response?.data?.detail || reason.message)), [filters]);
  useEffect(() => { load(); }, [load]);

  const review = async (row, decision) => {
    setError('');
    try {
      const meta = metadata[row.candidate_sample_id] || {};
      await api.post(`/candidates/${row.candidate_sample_id}/review`, {
        decision,
        proposed_label: decision === 'approve' ? (labels[row.candidate_sample_id] || row.proposed_label || 'Misleading') : null,
        language: decision === 'approve' ? (meta.language || row.language || 'Taglish') : null,
        topic: decision === 'approve' ? (meta.topic || row.topic || TOPICS[7]) : null,
        claim_group_id: decision === 'approve' ? (meta.claim_group_id || row.claim_group_id || `claim-${row.candidate_sample_id}`) : null,
      });
      await load();
    } catch (reason) { setError(reason.response?.data?.detail || reason.message); }
  };

  const openEvidence = async (row) => {
    setSelected(row);
    const { data } = await api.get(`/candidates/${row.candidate_sample_id}/evidence`);
    setEvidence(data.evidence);
  };

  const addEvidence = async (event) => {
    event.preventDefault();
    try {
      await api.post(`/candidates/${selected.candidate_sample_id}/evidence`, form);
      await openEvidence(selected);
      await load();
      setForm(EMPTY_EVIDENCE);
    } catch (reason) { setError(reason.response?.data?.detail || reason.message); }
  };

  const searchFactChecks = async () => {
    try {
      const { data } = await api.get(`/candidates/${selected.candidate_sample_id}/fact-check-search`);
      if (!data.matches?.length) return setError('No matching published fact check was found.');
      const match = data.matches[0];
      setForm({ ...form, source_url: match.url || '', publisher: match.publisher || '', rating: match.rating || '', notes: `Suggested match: ${match.claim || match.title || ''}` });
    } catch (reason) { setError(reason.response?.data?.detail || reason.message); }
  };

  const downloadExport = async (format) => {
    setExporting(format);
    setError('');
    try {
      const params = { format, ...Object.fromEntries(Object.entries(filters).filter(([, value]) => value)) };
      const response = await api.get('/candidates-export', { params, responseType: 'blob' });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = `suriph-candidates-${new Date().toISOString().slice(0, 10)}.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (reason) { setError(reason.response?.data?.detail || reason.message); }
    finally { setExporting(''); }
  };

  return <div>
    <h1>Candidate and evidence review</h1>
    <p style={{ color: 'var(--text-secondary)' }}>Only content that a user explicitly consents to submit enters this private queue. Auto-topics and model labels remain suggestions until human review; nothing enters a dataset automatically.</p>
    {error && <p style={{ color: 'var(--danger)', marginTop: 12 }}>{error}</p>}

    <section className="card" style={{ marginTop: 20 }}><h2>Candidate intake</h2>
      <div className="summary-grid" style={{ marginTop: 14 }}><div><strong>{intake.totals.candidates || 0}</strong><small>Total</small></div><div><strong style={{ color: 'var(--danger)' }}>{intake.totals.misleading || 0}</strong><small>Misleading</small></div><div><strong style={{ color: 'var(--success)' }}>{intake.totals.non_misleading || 0}</strong><small>Non-Misleading</small></div><div><strong>{intake.totals.missing_evidence || 0}</strong><small>Needs evidence</small></div></div>
      <h3 style={{ marginTop: 20 }}>Filter and export</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(210px,1fr))', gap: 10, marginTop: 12 }}>
        <select value={filters.topic} onChange={(event) => setFilters({ ...filters, topic: event.target.value })}><option value="">All eight topics</option>{TOPICS.map((topic) => <option key={topic}>{topic}</option>)}</select>
        <select value={filters.validation_status} onChange={(event) => setFilters({ ...filters, validation_status: event.target.value })}><option value="">All review statuses</option><option value="pending">Pending</option><option value="needs_revision">Needs revision</option><option value="approved">Approved</option><option value="excluded">Excluded</option></select>
        <select value={filters.evidence_status} onChange={(event) => setFilters({ ...filters, evidence_status: event.target.value })}><option value="">All evidence statuses</option><option value="missing">Missing evidence</option><option value="unverified">Evidence needs verification</option><option value="verified">Verified evidence</option></select>
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}><button className="btn-primary" disabled={Boolean(exporting)} onClick={() => downloadExport('xlsx')}>{exporting === 'xlsx' ? 'Preparing…' : 'Download Excel'}</button><button className="ghost-btn" disabled={Boolean(exporting)} onClick={() => downloadExport('csv')}>{exporting === 'csv' ? 'Preparing…' : 'Download CSV'}</button></div>
      <details style={{ marginTop: 18 }}><summary style={{ cursor: 'pointer', color: 'var(--text-secondary)' }}>View counts for all eight topics</summary><div style={{ overflowX: 'auto', marginTop: 12 }}><table><thead><tr><th>Topic</th><th>Total</th><th>Misleading</th><th>Non-Misleading</th><th>Needs evidence</th></tr></thead><tbody>{intake.topics.map((row) => <tr key={row.topic}><td>{row.topic}</td><td>{row.total}</td><td>{row.misleading}</td><td>{row.non_misleading}</td><td>{row.missing_evidence}</td></tr>)}</tbody></table></div></details>
    </section>

    <div className="card" style={{ overflowX: 'auto', marginTop: 20 }}><table><thead><tr><th>ID</th><th>Text and provenance</th><th>Auto topic</th><th>Proposed label</th><th>Status</th><th>Review decision</th></tr></thead><tbody>
      {rows.length ? rows.map((row) => {
        const meta = metadata[row.candidate_sample_id] || {};
        return <tr key={row.candidate_sample_id}>
          <td>{row.candidate_sample_id}</td>
          <td style={{ minWidth: 340 }}><p>{row.text_content}</p><small style={{ color: 'var(--text-secondary)' }}>{row.source_type} · {row.page_title || row.page_url || 'No page metadata'}</small></td>
          <td style={{ minWidth: 220 }}><strong>{row.topic || TOPICS[7]}</strong><br/><small>{row.topic_confidence != null ? `${Math.round(row.topic_confidence * 100)}% auto-topic confidence` : 'Topic confidence unavailable'}</small><br/><small>{row.topic_review_status}</small></td>
          <td style={{ minWidth: 180 }}><strong style={{ display: 'inline-block', color: (labels[row.candidate_sample_id] || row.proposed_label) === 'Misleading' ? 'var(--danger)' : 'var(--success)', marginBottom: 8 }}>{labels[row.candidate_sample_id] || row.proposed_label || 'Non-Misleading'}</strong><select aria-label={`Proposed label for candidate ${row.candidate_sample_id}`} value={labels[row.candidate_sample_id] || row.proposed_label || 'Non-Misleading'} onChange={(event) => setLabels({ ...labels, [row.candidate_sample_id]: event.target.value })}><option>Misleading</option><option>Non-Misleading</option></select><small style={{ display: 'block', marginTop: 6, color: 'var(--text-secondary)' }}>Model suggestion; confirm during review.</small></td>
          <td>{row.validation_status}<br/><small>{row.training_status}</small><br/><strong style={{ color: row.evidence_status === 'verified' ? 'var(--success)' : 'var(--warning)' }}>{row.evidence_status === 'missing' ? 'Evidence required' : row.evidence_status === 'unverified' ? 'Verify evidence' : 'Evidence verified'}</strong></td>
          <td style={{ minWidth: 320 }}>
            <select value={meta.language || row.language || 'Taglish'} onChange={(event) => setMetadata({ ...metadata, [row.candidate_sample_id]: { ...meta, language: event.target.value } })}><option>Taglish</option><option>Filipino</option><option>English</option></select>
            <select value={meta.topic || row.topic || TOPICS[7]} onChange={(event) => setMetadata({ ...metadata, [row.candidate_sample_id]: { ...meta, topic: event.target.value } })}>{TOPICS.map((topic) => <option key={topic}>{topic}</option>)}</select>
            <input placeholder="Claim group ID" value={meta.claim_group_id || row.claim_group_id || ''} onChange={(event) => setMetadata({ ...metadata, [row.candidate_sample_id]: { ...meta, claim_group_id: event.target.value } })}/>
            <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}><button className="btn-primary" disabled={row.evidence_status !== 'verified'} title={row.evidence_status === 'verified' ? 'Approve candidate' : 'Confirm a matching evidence URL first'} onClick={() => review(row, 'approve')}>Approve</button><button className="ghost-btn" onClick={() => review(row, 'revise')}>Revise</button><button className="ghost-btn" onClick={() => review(row, 'exclude')}>Exclude</button><button className="ghost-btn" onClick={() => openEvidence(row)}>Evidence ({row.evidence_count})</button></div>
          </td>
        </tr>;
      }) : <tr><td colSpan="6">No candidate samples match these filters.</td></tr>}
    </tbody></table></div>

    {selected && <section className="card" style={{ marginTop: 20 }}><h2>Evidence for candidate {selected.candidate_sample_id}</h2><p style={{ color: 'var(--text-secondary)', margin: '8px 0 16px' }}>Google Fact Check results are suggestions only. Confirm claim correspondence before marking an evidence record as matched.</p><button className="ghost-btn" onClick={searchFactChecks}>Search published fact checks</button>
      <form onSubmit={addEvidence} style={{ display: 'grid', gap: 10, marginTop: 14 }}><input type="url" required placeholder="Evidence URL" value={form.source_url} onChange={(event) => setForm({ ...form, source_url: event.target.value })}/><input placeholder="Publisher" value={form.publisher} onChange={(event) => setForm({ ...form, publisher: event.target.value })}/><input placeholder="Published rating if applicable" value={form.rating} onChange={(event) => setForm({ ...form, rating: event.target.value })}/><select value={form.claim_match_status} onChange={(event) => setForm({ ...form, claim_match_status: event.target.value })}><option value="unreviewed">Unreviewed</option><option value="matched">Same claim confirmed</option><option value="not_matched">Not the same claim</option></select><textarea rows="3" placeholder="Reviewer notes" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })}/><button className="btn-primary">Save evidence record</button></form>
      <ul style={{ marginTop: 18, display: 'grid', gap: 8 }}>{evidence.map((item) => <li key={item.evidence_record_id}><a href={item.source_url} target="_blank" rel="noreferrer">{item.publisher || item.source_url}</a> — {item.claim_match_status}{item.rating ? ` (${item.rating})` : ''}</li>)}</ul>
    </section>}
  </div>;
}
