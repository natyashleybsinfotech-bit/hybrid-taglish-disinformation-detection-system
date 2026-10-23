import { useEffect, useState } from 'react';
import { api } from '../api.js';

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => { Promise.all([api.get('/system-status'), api.get('/stats')]).then(([status, stats]) => setData({ status: status.data, stats: stats.data.stats })).catch((reason) => setError(reason.response?.data?.detail || reason.message)); }, []);
  if (error) return <div className="card"><h1>System status</h1><p style={{ color: 'var(--danger)' }}>{error}</p></div>;
  if (!data) return <p>Loading real service status…</p>;
  const services = { backend: data.status.backend, database: data.status.database.status, ...data.status.services };
  return <div><h1>System status</h1><p style={{ color: 'var(--text-secondary)' }}>Live readiness for the API, database, and evidence services.</p>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 16, margin: '24px 0' }}>
      {Object.entries(services).map(([name, value]) => <div className="card" key={name}><small>{name}</small><h3>{String(value)}</h3></div>)}
    </div>
    <div className="card"><h2>Decision engine</h2><p>Mode: {data.status.decision_engine?.mode}</p><p>Status: {data.status.decision_engine?.status}</p><p>Configured providers: {data.status.decision_engine?.configured_providers?.join(', ') || 'none'}</p><p>Classifier loaded: {String(data.status.decision_engine?.classifier_loaded)}</p><p>Audit events: {data.stats.audit_events}</p></div>
  </div>;
}
