import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Activity as ActivityIcon } from 'lucide-react';

const API_BASE = 'http://localhost:8000/admin-api';

export default function Activity() {
  const [logs, setLogs] = useState([]);
  const [filteredLogs, setFilteredLogs] = useState([]);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState('All');

  const fetchLogs = async () => {
    try {
      const res = await axios.get(`${API_BASE}/activity-log?limit=200`);
      setLogs(res.data.activity_log);
      setFilteredLogs(res.data.activity_log);
    } catch (err) {
      console.error("Failed to fetch activity logs", err);
    }
  };

  useEffect(() => {
    fetchLogs();
    const iv = setInterval(fetchLogs, 15000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    let result = logs;
    if (filterType !== 'All') {
      result = result.filter(log => log.action === filterType || (filterType.includes('RETRAIN_') && log.action.startsWith('RETRAIN_')));
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(log => 
        log.action.toLowerCase().includes(q) || 
        (log.description && log.description.toLowerCase().includes(q)) ||
        (log.performed_by && log.performed_by.toLowerCase().includes(q))
      );
    }
    setFilteredLogs(result);
  }, [search, filterType, logs]);

  const getActionColor = (action) => {
    if (action === 'PREDICTION') return 'badge-indigo';
    if (action.includes('LOGIN') || action.includes('LOGOUT')) return 'badge-green';
    if (action.includes('RETRAIN')) return action.includes('FAILED') ? 'badge-red' : 'badge-amber';
    if (action === 'SYSTEM_START') return 'badge-secondary';
    if (action.includes('FAILED')) return 'badge-red';
    return 'badge-indigo';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>Activity Log</h1>
        <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Showing {filteredLogs.length} entries</div>
      </div>

      <div className="card" style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
        <input 
          type="text" 
          placeholder="Search logs..." 
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ flex: 1, minWidth: '200px' }}
        />
        <select 
          value={filterType} 
          onChange={e => setFilterType(e.target.value)}
        >
          <option value="All">All Actions</option>
          <option value="PREDICTION">PREDICTION</option>
          <option value="ADMIN_LOGIN">LOGIN / LOGOUT</option>
          <option value="RETRAIN_">RETRAINING EVENTS</option>
          <option value="SYSTEM_START">SYSTEM START</option>
        </select>
        <button onClick={() => { setSearch(''); setFilterType('All'); }} className="ghost-btn" style={{ padding: '8px 16px', height: '100%' }}>
          Clear Filters
        </button>
      </div>

      <div className="card" style={{ overflowX: 'auto', padding: 0 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
          <thead>
            <tr style={{ backgroundColor: '#0f172a', borderBottom: '1px solid var(--border)' }}>
              <th style={{ textAlign: 'left', padding: '12px', color: 'var(--text-secondary)' }}>ID</th>
              <th style={{ textAlign: 'left', padding: '12px', color: 'var(--text-secondary)' }}>Action</th>
              <th style={{ textAlign: 'left', padding: '12px', color: 'var(--text-secondary)' }}>Description</th>
              <th style={{ textAlign: 'left', padding: '12px', color: 'var(--text-secondary)' }}>Performed By</th>
              <th style={{ textAlign: 'left', padding: '12px', color: 'var(--text-secondary)' }}>IP</th>
              <th style={{ textAlign: 'left', padding: '12px', color: 'var(--text-secondary)' }}>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {filteredLogs.length === 0 ? <tr><td colSpan={6} style={{ textAlign: 'center', padding: '24px', color: 'var(--text-secondary)' }}>No activity found</td></tr> :
              filteredLogs.map(log => (
                <tr key={log.log_id} style={{ borderBottom: '1px solid var(--border)' }} className="hover-row">
                  <td style={{ padding: '12px', color: 'var(--text-secondary)' }}>#{log.log_id}</td>
                  <td style={{ padding: '12px' }}>
                    <span className={`badge ${getActionColor(log.action)}`} style={{ padding: '4px 8px', borderRadius: '4px' }}>
                      {log.action}
                    </span>
                  </td>
                  <td style={{ padding: '12px', maxWidth: '400px' }}>{log.description}</td>
                  <td style={{ padding: '12px', color: 'var(--text-secondary)' }}>{log.performed_by}</td>
                  <td style={{ padding: '12px', color: 'var(--text-secondary)' }}>{log.ip_address || '-'}</td>
                  <td style={{ padding: '12px', color: 'var(--text-secondary)' }}>
                    {new Date(log.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'medium' })}
                  </td>
                </tr>
              ))
            }
          </tbody>
        </table>
      </div>
    </div>
  );
}
