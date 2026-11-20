import { Cpu } from 'lucide-react';
import { HashCopy, SectionTitle, StatusBadge } from './AdminUI.jsx';

export default function ActivePipeline({ runtime, error = '' }) {
  const external = runtime?.mode === 'gemini';
  const evidenceOnly = runtime?.mode === 'evidence_only';
  const description = external
    ? 'The external AI classifier currently selected for post screening.'
    : evidenceOnly ? 'Evidence-only screening is selected; the hybrid classifier is disabled.'
      : runtime ? 'The selected local hybrid profile.' : 'Loading the selected analysis pipeline.';
  return <section className="card dashboard-section">
    <SectionTitle icon={Cpu} title="Active inference pipeline" description={description} />
    {error && <p className="error-card">{error}</p>}
    <div className="detail-list">
      <div><span>Classifier</span><strong>{external ? 'External AI classifier' : evidenceOnly ? 'Evidence-only screening' : runtime?.classifier || (error ? 'Unavailable' : 'Loading…')}</strong></div>
      <div><span>{external ? 'Configuration status' : 'Status'}</span><StatusBadge value={runtime?.status || (error ? 'unavailable' : 'loading')} /></div>
      {external ? <>
        <div><span>Model version</span><strong>{runtime.name || 'Not reported'}</strong></div>
        <div><span>Execution</span><strong>Remote service</strong></div>
        <div><span>Local hybrid classifier</span><strong>{runtime.hybrid_classifier_active === false ? 'Inactive' : 'Not reported'}</strong></div>
      </> : runtime && !evidenceOnly ? <>
        <div><span>Device</span><strong>{runtime.device || 'Not reported'}</strong></div>
        <div><span>Training run</span><strong>{runtime.training_run_id || 'Not reported'}</strong></div>
        <div><span>Threshold</span><strong>{runtime.decision_threshold ?? 'Not reported'}</strong></div>
        <div><span>SHA-256</span><HashCopy value={runtime.sha256} /></div>
      </> : null}
    </div>
    {runtime && <p className="info-note">{runtime.local_trial ? 'This pipeline is active for local trial and is not approved for public deployment.' : evidenceOnly ? 'No local classifier is active in this mode.' : 'This is the selected local inference profile.'}</p>}
    <p className="muted-copy">{external ? 'Ready indicates that the service is configured. It does not guarantee external availability or establish prediction accuracy. Local training-run, threshold and weight-file fields do not apply to this mode.' : 'Historical registry entries below do not select the running classifier.'}</p>
  </section>;
}
