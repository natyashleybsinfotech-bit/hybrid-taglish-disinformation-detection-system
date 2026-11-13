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
import ErrorBoundary from './components/ErrorBoundary.jsx';

export function Layout({ children, onLogout, user }) {
  const links = [
    ['/performance', ActivityIcon, 'Model performance'],
    ...(user.role === 'admin' ? [
      ['/candidates', Database, 'Candidate samples'],
      ['/governance', GitBranch, 'Dataset and models'],
      ['/activity', ActivityIcon, 'Audit log'],
      ['/status', LayoutDashboard, 'System status'],
    ] : [
      ['/', LayoutDashboard, 'System status'],
    ]),
  ];
  return (
    <div className="admin-layout">
      <aside className="admin-sidebar">
        <div className="sidebar-top">
          <div className="sidebar-brand"><span className="login-brand-icon"><ShieldCheck size={23} /></span><div><strong>SuriPH</strong><small>ADMIN CONSOLE</small></div></div>
        </div>
        <p className="sidebar-role">{user.role === 'viewer' ? 'AFP evaluation · view only' : 'System administration'}</p>
        <p className="sidebar-nav-label">WORKSPACE</p>
        <nav className="sidebar-nav" aria-label="Admin navigation">
          {links.map(([to, Icon, label]) => <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}><Icon size={17} /><span>{label}</span></NavLink>)}
        </nav>
        <button type="button" className="nav-link sidebar-logout" onClick={onLogout}>
          <LogOut size={17} /><span>Log out</span>
        </button>
      </aside>
      <main className="admin-main"><div className="admin-content">{children}</div></main>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const logout = async () => {
    try { await api.post('/logout'); } catch { /* Clear the local session even if the API is unavailable. */ }
    localStorage.removeItem('admin_token');
    setUser(null);
  };
  const handleLogin = (data) => {
    window.history.replaceState(window.history.state, '', data.role === 'admin' ? '/performance' : '/');
    setUser(data);
  };
  useEffect(() => {
    localStorage.removeItem('admin_token');
    api.get('/check-auth').then(({ data }) => setUser(data)).catch(() => localStorage.removeItem('admin_token')).finally(() => setLoading(false));
  }, []);
  if (loading) return <p style={{ padding: 40 }}>Checking administrator session…</p>;
  if (!user) return <Login onLogin={handleLogin} />;
  return (
    <ErrorBoundary><BrowserRouter><Layout user={user} onLogout={logout}><Routes>
      <Route path="/" element={user.role === 'admin' ? <Navigate to="/performance" replace /> : <Dashboard />} />
      <Route path="/status" element={<Dashboard />} />
      <Route path="/performance" element={<Performance />} />
      {user.role === 'admin' && <Route path="/candidates" element={<Candidates />} />}
      {user.role === 'admin' && <Route path="/governance" element={<Governance />} />}
      {user.role === 'admin' && <Route path="/activity" element={<Activity />} />}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes></Layout></BrowserRouter></ErrorBoundary>
  );
}
