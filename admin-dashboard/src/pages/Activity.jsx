import { useEffect, useState } from 'react';
import { Activity as ActivityIcon, ClipboardList, FileClock } from 'lucide-react';
import { api } from '../api.js';
import { EmptyState, HashCopy, PageHeader, SectionTitle, StatusBadge } from '../components/AdminUI.jsx';

export default function Activity() {
  const [rows, setRows] = useState([]);
  const [decisions, setDecisions] = useState([]);
  const [error, setError] = useState('');
  useEffect(() => { api.get('/audit-logs').then(({ data }) => setRows(data.audit_logs)).catch((reason) => setError(reason.response?.data?.detail || reason.message)); }, []);
  useEffect(() => { api.get('/screening-decisions').then(({ data }) => setDecisions(data.decisions)).catch((reason) => setError(reason.response?.data?.detail || reason.message)); }, []);
  return <div>
    <PageHeader icon={ActivityIcon} title="Audit log" description="Review administrator events and recorded screening decisions." />
    {error && <p className="error-card">{error}</p>}
    <section className="card dashboard-section"><SectionTitle icon={FileClock} title="Administrator activity" description="Recent actions in the administration panel." /><div className="table-wrap"><table><thead><tr><th>ID</th><th>Action</th><th>Description</th><th>Actor</th><th>Created</th></tr></thead><tbody>
      {rows.length ? rows.map((row) => <tr key={row.audit_log_id}><td>{row.audit_log_id}</td><td><StatusBadge value={row.action} /></td><td>{row.description}</td><td>{row.performed_by}</td><td>{new Date(row.created_at).toLocaleString()}</td></tr>) : <tr><td colSpan="5"><EmptyState icon={FileClock} title="No audit events" description="Administrator actions will appear here when recorded." /></td></tr>}
    </tbody></table></div></section>
    <section className="card dashboard-section"><SectionTitle icon={ClipboardList} title="Screening decisions" description="Submitted text is represented by its SHA-256 hash; model and final decisions are recorded separately." /><div className="table-wrap"><table><thead><tr><th>ID</th><th>Text hash</th><th>Model label</th><th>Model score</th><th>Evidence</th><th>Source URLs</th><th>Final label</th><th>Reason</th><th>Changed</th></tr></thead><tbody>
      {decisions.length ? decisions.map(row => <tr key={row.screening_decision_id}><td>{row.screening_decision_id}</td><td><HashCopy value={row.text_sha256} /></td><td>{row.model_label}</td><td>{Number(row.model_score).toFixed(3)}</td><td><StatusBadge value={row.evidence_assessment} /></td><td>{(row.source_urls || []).map(url => <div key={url}><a href={url} target="_blank" rel="noopener noreferrer">{url}</a></div>)}</td><td>{row.final_label}</td><td>{row.final_reason}</td><td><StatusBadge value={row.evidence_adjusted ? 'Yes' : 'No'} tone={row.evidence_adjusted ? 'indigo' : 'secondary'} /></td></tr>) : <tr><td colSpan="9"><EmptyState icon={ClipboardList} title="No recorded decisions" description="Screening records will appear here when available." /></td></tr>}
    </tbody></table></div></section>
  </div>;
}
