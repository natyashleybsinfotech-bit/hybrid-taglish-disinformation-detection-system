import { useEffect, useState } from 'react';
import { Activity, Database, FileCheck2, LayoutDashboard, RefreshCw, Server, ShieldCheck } from 'lucide-react';
import { api } from '../api.js';
import ActivePipeline from '../components/ActivePipeline.jsx';
import { PageHeader, SectionTitle, StatCard, StatusBadge } from '../components/AdminUI.jsx';

const serviceNames = { backend: 'API', database: 'Database', easyocr: 'Image text reader', whisper: 'Video speech reader', ffmpeg: 'Video processor', serper: 'Source search', google_fact_check: 'Admin fact-check search' };
async function loadStatus() {
  const [status, stats] = await Promise.all([api.get('/system-status'), api.get('/stats')]);
  return { status: status.data, stats: stats.data.stats, checkedAt: new Date() };
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  useEffect(() => { let active = true; loadStatus().then(value => { if (active) setData(value); }).catch(reason => { if (active) setError(reason.response?.data?.detail || reason.message); }); return () => { active = false; }; }, []);
  const refresh = async () => {
    setRefreshing(true);
    try { setData(await loadStatus()); setError(''); }
    catch (reason) { setError(reason.response?.data?.detail || reason.message); }
    finally { setRefreshing(false); }
  };
  const refreshButton = <button type="button" className="ghost-btn status-refresh" onClick={refresh} disabled={refreshing}><RefreshCw size={16} />{refreshing ? 'Checking…' : 'Refresh status'}</button>;
  if (error) return <div><PageHeader icon={LayoutDashboard} title="System status" description="The latest service check could not be completed. Refresh to try again." actions={refreshButton} /><div className="card error-card" role="alert">{error}</div></div>;
  if (!data) return <p className="page-loading">Loading real service status…</p>;
  const services = { backend: data.status.backend, database: data.status.database.status, ...Object.fromEntries(Object.keys(serviceNames).filter(name => name in (data.status.services || {})).map(name => [name, data.status.services[name]])) };
  return <div>
    <PageHeader icon={LayoutDashboard} title="System status" description={`Last checked ${data.checkedAt.toLocaleTimeString()}. Refresh after restarting a service.`} actions={refreshButton} />
    <section className="dashboard-section"><SectionTitle icon={Activity} title="Service health" description="Configured means a key is present; it does not confirm that a live provider request will succeed." />
      <div className="service-grid">{Object.entries(services).map(([name, value]) => <div className="service-card" key={name}><span className="service-icon">{name === 'database' ? <Database size={20} /> : name === 'backend' ? <Server size={20} /> : <ShieldCheck size={20} />}</span><small>{serviceNames[name]}</small><StatusBadge value={value} /></div>)}</div>
    </section>
    <ActivePipeline runtime={data.status.model} />
    <section className="card dashboard-section"><SectionTitle icon={Database} title="Database records" description={data.status.screening_mode === 'evidence_only' ? 'Current records. The text classifier is disabled in prototype mode.' : 'Current records and active model identity.'} />
      <div className="summary-grid dashboard-stats"><StatCard icon={FileCheck2} value={data.stats.candidate_samples} label="Candidate samples" /><StatCard icon={Activity} value={data.stats.pending_candidates} label="Pending validation" tone="amber" /><StatCard icon={ShieldCheck} value={data.stats.audit_events} label="Audit events" tone="green" /></div>
      <div className="detail-list"><div><span>Screening mode</span><StatusBadge value={data.status.screening_mode || 'model'} /></div><div><span>Classifier status</span><StatusBadge value={data.status.model_status} /></div><div><span>Model</span><strong>{data.status.screening_mode === 'evidence_only' ? 'Disabled' : data.status.model?.name || 'Unavailable'}</strong></div><div><span>Version</span><strong>{data.status.screening_mode === 'evidence_only' ? 'Not used' : data.status.model?.version || 'N/A'}</strong></div></div>
      {data.status.screening_mode === 'model' && data.status.model?.local_trial && <p className="page-context" role="note">Local trial model only — its reported metrics measure agreement with inherited dataset labels, not independently verified accuracy on real Facebook posts. Model scores are not factual certainty; check the cited sources and original context.</p>}
    </section>
    <section className="card dashboard-section"><SectionTitle icon={FileCheck2} title="Media reader settings" description={data.status.screening_mode === 'evidence_only' ? 'Image text and video speech extraction remain active; screening uses retrieved source evidence only.' : 'Image text and video speech are extracted before the selected classifier checks them.'} /><div className="detail-list"><div><span>Speech model</span><strong>{data.status.services?.whisper_model || 'Not reported'}</strong></div><div><span>Language hint</span><strong>{data.status.services?.whisper_language_hint === 'tl' ? 'Filipino / Taglish' : data.status.services?.whisper_language_hint || 'Not reported'}</strong></div><div><span>Speech boundary detection</span><strong>{data.status.services?.whisper_vad_filter == null ? 'Not reported' : data.status.services.whisper_vad_filter ? 'Enabled' : 'Disabled'}</strong></div></div></section>
  </div>;
}
