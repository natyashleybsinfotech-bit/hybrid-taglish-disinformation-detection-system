import { useEffect, useState } from 'react';
import { BrowserRouter, Navigate, NavLink, Route, Routes } from 'react-router-dom';
import { Activity as ActivityIcon, Database, LayoutDashboard, LogOut, ShieldCheck } from 'lucide-react';
import { api } from './api.js';
import Activity from './pages/Activity.jsx';
import Candidates from './pages/Candidates.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Login from './pages/Login.jsx';

function Layout({ children, onLogout }) {
  const logout = async () => {
    try { await api.post('/logout'); } catch { /* Clear the local session even if the API is unavailable. */ }
    localStorage.removeItem('admin_token');
    onLogout();
  };
  const links = [
    ['/', LayoutDashboard, 'System status'],
    ['/candidates', Database, 'Candidate samples'],
    ['/activity', ActivityIcon, 'Audit log'],
  ];
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <aside style={{ width: 240, padding: 20, borderRight: '1px solid var(--border)', background: 'var(--bg-sidebar)' }}>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 8 }}><ShieldCheck color="var(--accent)" /> SuriPH</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: 12 }}>Sprint 1 administration</p>
        <nav style={{ display: 'grid', gap: 8, marginTop: 28 }}>
          {links.map(([to, Icon, label]) => <NavLink key={to} to={to} style={({ isActive }) => ({ padding: 12, borderRadius: 8, color: 'white', textDecoration: 'none', background: isActive ? 'var(--accent)' : 'transparent' })}><Icon size={16} style={{ marginRight: 8, verticalAlign: 'middle' }} />{label}</NavLink>)}
        </nav>
        <button className="ghost-btn" onClick={logout} style={{ marginTop: 30 }}><LogOut size={16} /> Log out</button>
      </aside>
      <main style={{ flex: 1, padding: 32 }}>{children}</main>
    </div>
  );
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(() => Boolean(localStorage.getItem('admin_token')));
  useEffect(() => {
    if (!localStorage.getItem('admin_token')) return;
    api.get('/check-auth').then(() => setAuthenticated(true)).catch(() => localStorage.removeItem('admin_token')).finally(() => setLoading(false));
  }, []);
  if (loading) return <p style={{ padding: 40 }}>Checking administrator session…</p>;
  if (!authenticated) return <Login onLogin={() => setAuthenticated(true)} />;
  return (
    <BrowserRouter><Layout onLogout={() => setAuthenticated(false)}><Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/candidates" element={<Candidates />} />
      <Route path="/activity" element={<Activity />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes></Layout></BrowserRouter>
  );
}
