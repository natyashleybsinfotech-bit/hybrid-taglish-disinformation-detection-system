import { useState } from 'react';
import { api } from '../api.js';

export default function Research() {
  const [busy, setBusy] = useState(false), [message, setMessage] = useState('');
  async function download() {
    if (busy) return;
    setBusy(true); setMessage('');
    try {
      const response = await api.get('/research-export', { responseType: 'blob' });
      const url = URL.createObjectURL(response.data), link = document.createElement('a');
      link.href = url; link.download = 'suriph-research.csv'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      setMessage('Export downloaded. Keep it private and delete it under the study retention policy.');
    } catch { setMessage('Research export is unavailable. Check your session and database connection.'); }
    finally { setBusy(false); }
  }
  return <div><h1>Participant research</h1><p className="page-subtitle">Voluntary feedback, separate from candidate curation and model training.</p>
    <section className="card" style={{ marginTop: 24 }}><h2>Consent comes first</h2><p>Ordinary screening is not saved. Participants may opt in to saving a result and its seven measured text signals. Text and evidence links require a separate opt-in. Page metadata and direct identifiers are not collected in research records.</p><p>The extension provides a receipt to withdraw a record or add a usefulness rating. A usefulness rating is not a validated survey score or a factual label.</p></section>
    <section className="card" style={{ marginTop: 20 }}><h2>Pseudonymous analysis export</h2><p>Exports contain random record IDs, consent version, input type, optional usefulness, prediction, model score, model identity and feature measurements. They exclude text, evidence links and withdrawal tokens.</p><button className="btn-primary" disabled={busy} onClick={download}>{busy ? 'Preparing export…' : 'Download research CSV'}</button><p role="status" aria-live="polite">{message}</p></section>
    <section className="card" style={{ marginTop: 20 }}><h2>Before inviting participants</h2><p>Use the draft questionnaires and pilot checklist in docs/research. Obtain the required institutional review, fill in the study contact and confirm retention. Keep BSIT and AFP responses separate. No participant responses or evaluation scores have been fabricated.</p><p>Run scheduled retention cleanup and private logical backups. Restored backups must be checked against withdrawal requests before reopening access.</p></section>
  </div>;
}
