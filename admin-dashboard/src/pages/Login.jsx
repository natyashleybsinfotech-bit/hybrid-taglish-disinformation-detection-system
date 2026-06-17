import React, { useState } from 'react';
import axios from 'axios';
import { ShieldCheck } from 'lucide-react';

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const API_BASE = 'http://localhost:8000/admin-api';

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const res = await axios.post(`${API_BASE}/login`, {
        username,
        password
      });
      if (res.data.status === 'success') {
        localStorage.setItem('admin_token', res.data.token);
        onLogin(res.data.token);
      }
    } catch (err) {
      setError('Invalid credentials.');
    }
  };

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      minHeight: '100vh'
    }}>
      <div className="card" style={{ width: '400px', padding: '40px 32px' }}>
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <ShieldCheck size={64} color="var(--accent)" style={{ margin: '0 auto 16px', filter: 'drop-shadow(0 0 10px rgba(99, 102, 241, 0.4))' }} />
          <h1 style={{ fontSize: '20px', fontWeight: 'bold', margin: '0 0 4px 0' }}>Taglish Disinformation Detection System</h1>
          <div style={{ fontSize: '12px', color: '#f59e0b', marginTop: '12px', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '1px' }}>Administrator Access Only</div>
        </div>

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <label style={{ fontSize: '12px', color: '#94a3b8', fontWeight: 'bold', textTransform: 'uppercase' }}>Username</label>
            <input 
              type="text" 
              placeholder="Enter your username" 
              value={username}
              onChange={e => setUsername(e.target.value)}
              style={{ width: '100%' }}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <label style={{ fontSize: '12px', color: '#94a3b8', fontWeight: 'bold', textTransform: 'uppercase' }}>Password</label>
            <input 
              type="password" 
              placeholder="Enter your password" 
              value={password}
              onChange={e => setPassword(e.target.value)}
              style={{ width: '100%' }}
            />
          </div>

          {error && <div style={{ color: '#ef4444', fontSize: '13px', textAlign: 'center' }}>{error}</div>}
          
          <button type="submit" className="btn-primary" style={{ width: '100%', marginTop: '8px', padding: '14px' }}>
            Sign In to Dashboard
          </button>
        </form>
      </div>
    </div>
  );
}
