import { useEffect, useState } from 'react';
import { BrowserRouter, Navigate, NavLink, Route, Routes } from 'react-router-dom';
import { Activity as ActivityIcon, Database, GitBranch, LayoutDashboard, LogOut, ShieldCheck } from 'lucide-react';
import { api } from './api.js';
import Activity from './pages/Activity.jsx';
import Candidates from './pages/Candidates.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Login from './pages/Login.jsx';
import Governance from './pages/Governance.jsx';
import Performance from './pages/Performance.jsx';
import Research from './pages/Research.jsx';
import ErrorBoundary from './components/ErrorBoundary.jsx';

export function Layout({ children, onLogout, user }) {
  const logout = async () => {
    try { await api.post('/logout'); } catch { /* Clear the local session even if the API is unavailable. */ }
    localStorage.removeItem('admin_token');
    onLogout();
  };
  const links = [
    ['/performance', ActivityIcon, 'Model performance'],
    ...(user.role === 'admin' ? [
      ['/research', ShieldCheck, 'Participant research'],
      ['/candidates', Database, 'Candidate samples'],
      ['/governance', GitBranch, 'Dataset and models'],
      ['/activity', ActivityIcon, 'Audit log'],
      ['/', LayoutDashboard, 'System status'],
    ] : [
      ['/', LayoutDashboard, 'System status'],
    ]),
  ];
  return (
    <div className="admin-layout" style={{ display: 'flex', minHeight: '100vh' }}>
      <aside style={{ width: 240, padding: 20, borderRight: '1px solid var(--border)', background: 'var(--bg-sidebar)' }}>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 8 }}><ShieldCheck color="var(--accent)" /> SuriPH</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{user.role === 'viewer' ? 'AFP evaluation Â· view only' : 'Research administration'}</p>
        <nav style={{ display: 'grid', gap: 8, marginTop: 28 }}>
          {links.map(([to, Icon, label]) => <NavLink key={to} to={to} style={({ isActive }) => ({ padding: 12, borderRadius: 8, color: 'white', textDecoration: 'none', background: isActive ? 'var(--accent)' : 'transparent' })}><Icon size={16} style={{ marginRight: 8, verticalAlign: 'middle' }} />{label}</NavLink>)}
        </nav>
        <button className="ghost-btn" onClick={logout} style={{ marginTop: 30 }}><LogOut size={16} /> Log out</button>
      </aside>
      <main className="admin-main" style={{ flex: 1, padding: 32 }}>{children}</main>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    localStorage.removeItem('admin_token');
    api.get('/check-auth').then(({ data }) => setUser(data)).catch(() => localStorage.removeItem('admin_token')).finally(() => setLoading(false));
  }, []);
  if (loading) return <p style={{ padding: 40 }}>Checking administrator sessionâ€¦</p>;
  if (!user) return <Login onLogin={(data) => setUser(data)} />;
  return (
    <ErrorBoundary><BrowserRouter><Layout user={user} onLogout={() => setUser(null)}><Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/performance" element={<Performance />} />
      {user.role === 'admin' && <Route path="/research" element={<Research />} />}
      {user.role === 'admin' && <Route path="/candidates" element={<Candidates />} />}
      {user.role === 'admin' && <Route path="/governance" element={<Governance />} />}
      {user.role === 'admin' && <Route path="/activity" element={<Activity />} />}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes></Layout></BrowserRouter></ErrorBoundary>
  );
}
