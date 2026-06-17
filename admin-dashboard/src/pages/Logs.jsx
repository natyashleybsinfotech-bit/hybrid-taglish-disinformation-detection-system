import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Download } from 'lucide-react';

const API_BASE = 'http://localhost:8000/admin-api';

export default function Logs() {
  const [data, setData] = useState([]);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('All');

  useEffect(() => {
    axios.get(`${API_BASE}/predictions?limit=200`)
      .then(res => setData(res.data.predictions || []))
      .catch(err => console.error("Failed to fetch logs", err));
  }, []);

  const filteredData = data.filter(row => {
    const matchesSearch = row.input_text.toLowerCase().includes(search.toLowerCase());
    const matchesFilter = filter === 'All' || row.label === filter;
    return matchesSearch && matchesFilter;
  });

  const exportCSV = () => {
    if (filteredData.length === 0) return;
    const headers = ["ID", "Text", "Label", "Confidence", "Code Switching", "Urgency", "Particles", "Punctuation", "Caps", "Repeats", "Emotional", "Inference(ms)", "Time"];
    let csv = headers.join(",") + "\n";
    filteredData.forEach(r => {
      const safeText = '"' + r.input_text.replace(/"/g, '""') + '"';
      csv += [r.id, safeText, r.label, r.confidence, r.code_switching_ratio, r.urgency_count, r.particle_count, r.punctuation_intensity, r.caps_ratio, r.repeated_chars, r.emotional_count, r.inference_ms, r.created_at].join(",") + "\n";
    });
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'taglish_predictions.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>Prediction Logs</h1>

      <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
        <input 
          type="text" 
          placeholder="Search text..." 
          style={{ flexGrow: 1 }}
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select value={filter} onChange={e => setFilter(e.target.value)}>
          <option value="All">All Labels</option>
          <option value="Disinformation">Disinformation</option>
          <option value="Non-Disinformation">Non-Disinformation</option>
        </select>
        <button className="btn-primary" onClick={exportCSV}>
          <Download size={16} /> Export CSV
        </button>
      </div>

      <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
        Showing {filteredData.length} of {data.length} predictions
      </div>

      <div className="card" style={{ padding: 0, overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', whiteSpace: 'nowrap' }}>
          <thead>
            <tr>
              {["ID", "Text", "Label", "Confidence", "CS Ratio", "Urgency", "Particles", "Punct", "Caps", "Repeat", "Emotional", "ms", "Time"].map((h, i) => (
                <th key={h} style={{ padding: '12px 16px', textAlign: i > 3 && i < 12 ? 'right' : 'left', color: 'var(--text-secondary)', fontWeight: 'normal', textTransform: 'uppercase', fontSize: '11px', borderBottom: '1px solid var(--border)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredData.length === 0 ? <tr><td colSpan={13} style={{ textAlign: 'center', padding: '20px' }}>No records found.</td></tr> :
              filteredData.map(row => {
                const isDisinfo = row.label === 'Disinformation';
                const confPct = (row.confidence * 100).toFixed(1);
                return (
                  <tr key={row.id} style={{ borderBottom: '1px solid var(--border)', transition: 'background 0.2s' }}>
                    <td style={{ padding: '12px 16px' }}>{row.id}</td>
                    <td style={{ padding: '12px 16px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis' }}>{row.input_text}</td>
                    <td style={{ padding: '12px 16px' }}><span className={`badge ${isDisinfo ? 'badge-red' : 'badge-green'}`}>{row.label}</span></td>
                    <td style={{ padding: '12px 16px' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <span>{confPct}%</span>
                        <div style={{ width: '30px', height: '4px', background: 'var(--border)', borderRadius: '2px' }}>
                          <div style={{ height: '100%', width: `${confPct}%`, background: isDisinfo ? 'var(--danger)' : 'var(--success)', borderRadius: '2px' }} />
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: '12px 16px', textAlign: 'right' }}>{row.code_switching_ratio.toFixed(4)}</td>
                    <td style={{ padding: '12px 16px', textAlign: 'right' }}>{row.urgency_count}</td>
                    <td style={{ padding: '12px 16px', textAlign: 'right' }}>{row.particle_count}</td>
                    <td style={{ padding: '12px 16px', textAlign: 'right' }}>{row.punctuation_intensity.toFixed(4)}</td>
                    <td style={{ padding: '12px 16px', textAlign: 'right' }}>{row.caps_ratio.toFixed(4)}</td>
                    <td style={{ padding: '12px 16px', textAlign: 'right' }}>{row.repeated_chars.toFixed(4)}</td>
                    <td style={{ padding: '12px 16px', textAlign: 'right' }}>{row.emotional_count}</td>
                    <td style={{ padding: '12px 16px', textAlign: 'right' }}>{row.inference_ms.toFixed(1)}</td>
                    <td style={{ padding: '12px 16px', color: 'var(--text-secondary)' }}>{new Date(row.created_at).toLocaleString()}</td>
                  </tr>
                );
              })
            }
          </tbody>
        </table>
      </div>
    </div>
  );
}
