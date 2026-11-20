import { Cpu } from 'lucide-react';
import { HashCopy, SectionTitle, StatusBadge } from './AdminUI.jsx';

export default function ActivePipeline({ runtime, error = '' }) {
  const evidenceOnly = runtime?.mode === 'evidence_only';
  const description = evidenceOnly ? 'Evidence-only screening is selected; the hybrid classifier is disabled.'
      : runtime ? 'The selected local hybrid profile.' : 'Loading the selected analysis pipeline.';
  return <section className="card dashboard-section">
    <SectionTitle icon={Cpu} title="Active inference pipeline" description={description} />
    {error && <p className="error-card">{error}</p>}
    <div className="detail-list">
      <div><span>Classifier</span><strong>{evidenceOnly ? 'Evidence-only screening' : runtime?.classifier || (error ? 'Unavailable' : 'Loading…')}</strong></div>
      <div><span>Status</span><StatusBadge value={runtime?.status || (error ? 'unavailable' : 'loading')} /></div>
      {runtime && !evidenceOnly ? <>
        <div><span>Device</span><strong>{runtime.device || 'Not reported'}</strong></div>
        <div><span>Training run</span><strong>{runtime.training_run_id || 'Not reported'}</strong></div>
        <div><span>Threshold</span><strong>{runtime.decision_threshold ?? 'Not reported'}</strong></div>
        <div><span>SHA-256</span><HashCopy value={runtime.sha256} /></div>
      </> : null}
    </div>
    {runtime && <p className="info-note">{runtime.local_trial ? 'This pipeline is active for local trial and is not approved for public deployment.' : evidenceOnly ? 'No local classifier is active in this mode.' : 'This is the selected local inference profile.'}</p>}
    <p className="muted-copy">Historical registry entries below do not select the running classifier.</p>
  </section>;
}
