import { useState } from 'react';
import { Activity, ArrowRight, Database, FileCheck2, ShieldCheck } from 'lucide-react';
import { api } from '../api.js';

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const login = async (event) => {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const { data } = await api.post('/login', { username, password });
      onLogin(data);
    } catch (reason) { setError(reason.response?.data?.detail || 'Administrator login failed.'); }
    finally { setBusy(false); }
  };
  return <main className="login-shell">
    <div className="login-glow login-glow-one" /><div className="login-glow login-glow-two" />
    <section className="login-layout">
      <div className="login-intro">
        <div className="login-brand"><span className="login-brand-icon"><ShieldCheck size={21} /></span><span>SuriPH</span></div>
        <p className="eyebrow">CONTENT INTELLIGENCE</p>
        <h1>Understand what you’re reading.</h1>
        <p className="intro-copy">A focused workspace for reviewing content signals, candidate samples, and system activity in one place.</p>
        <div className="intro-features">
          <div><span><FileCheck2 size={16} /></span><p><strong>Review signals</strong><small>Measured signals and model predictions</small></p></div>
          <div><span><Database size={16} /></span><p><strong>Curate samples</strong><small>Keep validation separate from training</small></p></div>
          <div><span><Activity size={16} /></span><p><strong>Track activity</strong><small>See health and audit events at a glance</small></p></div>
        </div>
      </div>
      <section className="login-card">
        <p className="card-kicker">ADMINISTRATOR ACCESS</p>
        <h2>Sign in</h2>
        <p className="login-subtitle">Enter your credentials to continue.</p>
        <form onSubmit={login} className="login-form">
          <label className="field-label">Username<input value={username} onChange={(event) => setUsername(event.target.value)} required autoComplete="username" placeholder="Enter your username" /></label>
          <label className="field-label">Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required autoComplete="current-password" placeholder="Enter your password" /></label>
          {error && <p role="alert" className="login-error">{error}</p>}
          <button className="btn-primary login-submit" disabled={busy}>{busy ? 'Signing in…' : 'Continue'} {!busy && <ArrowRight size={17} />}</button>
        </form>
        <div className="secure-note"><ShieldCheck size={14} /> Protected administrator area</div>
      </section>
    </section>
  </main>;
}
