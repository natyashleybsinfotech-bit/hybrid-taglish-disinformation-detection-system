import { useEffect, useState } from 'react';
import { api } from '../api.js';

export default function Performance() {
  const [engine, setEngine] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/system-status').then(({ data }) => setEngine(data.decision_engine)).catch((reason) => setError(reason.response?.data?.detail || reason.message));
  }, []);

  return <div>
    <h1>Evidence assessment</h1>
    <p style={{ color: 'var(--text-secondary)' }}>Live status for the evidence-only decision path.</p>
    {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
    <section className="card" style={{ marginTop: 20 }}>
      <h2>Active decision engine</h2>
      <p>{engine ? `${engine.mode}: ${engine.status}` : 'Runtime status unavailable'}</p>
      {engine && <>
        <p>Configured providers: {engine.configured_providers?.join(', ') || 'none'}</p>
        <p>Possible outcomes: {engine.outcomes?.join(', ')}</p>
        <p>Classifier loaded: <strong>{String(engine.classifier_loaded)}</strong></p>
      </>}
      <p>The active system does not load a trained classifier. Related articles provide context; only a closely matching published fact-check can supply its publisher’s rating.</p>
    </section>
  </div>;
}
