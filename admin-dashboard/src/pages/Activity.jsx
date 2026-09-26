import { useEffect, useState } from 'react';
import { api } from '../api.js';

export default function Activity() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');
  useEffect(() => { api.get('/audit-logs').then(({ data }) => setRows(data.audit_logs)).catch((reason) => setError(reason.response?.data?.detail || reason.message)); }, []);
  return <div><h1>Audit log</h1>{error && <p style={{ color: 'var(--danger)' }}>{error}</p>}<div className="card" style={{ overflowX: 'auto' }}><table><thead><tr><th>ID</th><th>Action</th><th>Description</th><th>Actor</th><th>Created</th></tr></thead><tbody>
    {rows.length ? rows.map((row) => <tr key={row.audit_log_id}><td>{row.audit_log_id}</td><td>{row.action}</td><td>{row.description}</td><td>{row.performed_by}</td><td>{new Date(row.created_at).toLocaleString()}</td></tr>) : <tr><td colSpan="5">No audit events.</td></tr>}
  </tbody></table></div></div>;
}
