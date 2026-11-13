import { useState } from 'react';
import { Check, Clipboard, Inbox } from 'lucide-react';
import { statusTone } from '../status.js';

export function PageHeader({ icon: Icon, title, description, actions }) {
  return <header className="page-header">
    <div className="page-heading"><span className="page-heading-icon"><Icon size={23} /></span><div><p className="page-eyebrow">SuriPH / Administration</p><h1>{title}</h1><p>{description}</p></div></div>
    {actions && <div className="page-actions">{actions}</div>}
  </header>;
}

export function SectionTitle({ icon: Icon, title, description, actions }) {
  return <div className="section-heading"><div className="section-title"><span className="section-icon"><Icon size={18} /></span><div><h2>{title}</h2>{description && <p>{description}</p>}</div></div>{actions && <div className="section-actions">{actions}</div>}</div>;
}

export function StatCard({ icon: Icon, label, value, tone = 'indigo' }) {
  return <div className={`stat-card stat-${tone}`}><span className="stat-icon"><Icon size={19} /></span><strong>{value}</strong><small>{label}</small></div>;
}

export function EmptyState({ icon: Icon = Inbox, title, description }) {
  return <div className="empty-state"><span className="empty-icon"><Icon size={24} /></span><strong>{title}</strong>{description && <p>{description}</p>}</div>;
}

export function StatusBadge({ value, tone }) {
  const normalized = String(value ?? 'unknown');
  const resolved = tone || statusTone(value);
  return <span className={`badge badge-${resolved}`}><span className="badge-dot" />{normalized.replaceAll('_', ' ')}</span>;
}

export function HashCopy({ value }) {
  const [copied, setCopied] = useState(false);
  const hash = value || 'unavailable';
  const copy = async () => { if (!value) return; try { await navigator.clipboard.writeText(value); setCopied(true); window.setTimeout(() => setCopied(false), 1800); } catch { setCopied(false); } };
  return <span className="hash-copy"><code title={hash}>{hash.length > 22 ? `${hash.slice(0, 12)}…${hash.slice(-8)}` : hash}</code>{value && <button type="button" className="icon-button" onClick={copy} aria-label={copied ? 'SHA-256 copied' : 'Copy SHA-256 hash'} title={copied ? 'Copied' : 'Copy full hash'}>{copied ? <Check size={15} /> : <Clipboard size={15} />}</button>}</span>;
}
