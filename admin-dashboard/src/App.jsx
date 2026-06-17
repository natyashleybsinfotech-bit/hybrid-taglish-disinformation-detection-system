import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate, useNavigate } from 'react-router-dom';
import { LayoutDashboard, List, Activity as ActivityIcon, RotateCcw, ShieldCheck, LogOut, TerminalSquare } from 'lucide-react';
import axios from 'axios';

// Pages
import Dashboard from './pages/Dashboard';
import Logs from './pages/Logs';
import Models from './pages/Models';
import Retrain from './pages/Retrain';
import Activity from './pages/Activity';
import Login from './pages/Login';

const API_BASE = "http://localhost:8000/admin-api";

// Axios Interceptor for Request
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

function AppLayout({ children, onLogout }) {
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await axios.post(`${API_BASE}/logout`);
    } catch(e) {}
    localStorage.removeItem('admin_token');
    onLogout();
    navigate('/');
  };

  const navLinkStyle = ({ isActive }) => ({
    display: 'flex', alignItems: 'center', gap: '12px', height: '44px', padding: '0 16px',
    borderRadius: '8px', color: isActive ? 'white' : 'var(--text-secondary)',
    backgroundColor: isActive ? 'var(--accent)' : 'transparent', textDecoration: 'none',
    fontSize: '14px', fontWeight: isActive ? '600' : '400', transition: 'all 0.2s',
  });

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <aside style={{ 
        width: '240px', 
        backgroundColor: 'var(--bg-sidebar)', 
        backdropFilter: 'var(--glass-blur)',
        WebkitBackdropFilter: 'var(--glass-blur)',
        borderRight: '1px solid var(--border)', 
        display: 'flex', 
        flexDirection: 'column', 
        position: 'fixed', 
        height: '100vh', 
        overflowY: 'auto',
        zIndex: 50
      }}>
        <div style={{ padding: '24px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <ShieldCheck size={32} color="var(--accent)" style={{ flexShrink: 0 }} />
          <div>
            <div style={{ fontSize: '14px', fontWeight: 'bold', color: 'white', lineHeight: '1.2' }}>Taglish Disinformation</div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Detection System</div>
          </div>
        </div>
        
        <nav style={{ padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
          {[
            { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
            { to: '/logs', icon: List, label: 'Prediction Logs' },
            { to: '/models', icon: ActivityIcon, label: 'Model Performance' },
            { to: '/retrain', icon: RotateCcw, label: 'Retrain Model' },
            { to: '/activity', icon: TerminalSquare, label: 'Activity Log' }
          ].map(link => (
            <NavLink
              key={link.to}
              to={link.to}
              style={navLinkStyle}
              onMouseEnter={(e) => {
                if(e.currentTarget.style.backgroundColor === 'transparent') {
                  e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)';
                }
              }}
              onMouseLeave={(e) => {
                if(e.currentTarget.style.backgroundColor === 'rgba(255, 255, 255, 0.05)') {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }
              }}
            >
              <link.icon size={18} />
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div style={{ padding: '16px 12px', borderTop: '1px solid var(--border)' }}>
          <button 
            onClick={handleLogout} 
            style={{ 
              display: 'flex', alignItems: 'center', gap: '12px', height: '44px', padding: '0 16px',
              borderRadius: '8px', color: 'var(--text-secondary)', backgroundColor: 'transparent',
              border: 'none', cursor: 'pointer', width: '100%', fontSize: '14px', transition: 'all 0.2s', textAlign: 'left'
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            <LogOut size={18} />
            Logout
          </button>
        </div>
      </aside>

      <main style={{ marginLeft: '240px', flex: 1, padding: '32px', maxWidth: 'calc(100vw - 240px)' }}>
        <div className="animate-fade-in">
          {children}
        </div>
      </main>
    </div>
  );
}

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('admin_token');
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        await axios.get('http://localhost:8000/admin-api/check-auth');
        setIsAuthenticated(true);
      } catch (err) {
        localStorage.removeItem('admin_token');
      }
      setLoading(false);
    };
    checkAuth();
  }, []);

  // Axios response interceptor for global 401 handling
  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      response => response,
      error => {
        if (error.response && error.response.status === 401) {
          setIsAuthenticated(false);
          localStorage.removeItem('admin_token');
        }
        return Promise.reject(error);
      }
    );
    return () => axios.interceptors.response.eject(interceptor);
  }, []);

  if (loading) return <div style={{ color: 'white', padding: '50px', backgroundColor: '#0f172a', minHeight: '100vh' }}>Loading...</div>;

  if (!isAuthenticated) {
    return <Login onLogin={() => setIsAuthenticated(true)} />;
  }

  return (
    <BrowserRouter>
      <AppLayout onLogout={() => setIsAuthenticated(false)}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/models" element={<Models />} />
          <Route path="/retrain" element={<Retrain />} />
          <Route path="/activity" element={<Activity />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </AppLayout>
    </BrowserRouter>
  );
}
