import { useEffect, useState } from 'react';
import { api } from '../api.js';

export default function Candidates() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');
  useEffect(() => { api.get('/candidates').then(({ data }) => setRows(data.candidates)).catch((reason) => setError(reason.response?.data?.detail || reason.message)); }, []);
  return <div><h1>Candidate samples</h1><p style={{ color: 'var(--text-secondary)' }}>Submissions stay pending and are not training data.</p>{error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
    <div className="card" style={{ overflowX: 'auto' }}><table><thead><tr><th>ID</th><th>Text</th><th>Validation</th><th>Training</th><th>Created</th></tr></thead><tbody>
      {rows.length ? rows.map((row) => <tr key={row.candidate_sample_id}><td>{row.candidate_sample_id}</td><td>{row.text_content}</td><td>{row.validation_status}</td><td>{row.training_status}</td><td>{new Date(row.submitted_at).toLocaleString()}</td></tr>) : <tr><td colSpan="5">No candidate samples.</td></tr>}
    </tbody></table></div>
  </div>;
}
