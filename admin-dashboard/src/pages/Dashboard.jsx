import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement } from 'chart.js';
import { Doughnut, Bar } from 'react-chartjs-2';
import { Search, AlertTriangle, CheckCircle, BarChart2 } from 'lucide-react';

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement);

const API_BASE = 'http://localhost:8000/admin-api';

export default function Dashboard() {
  const [stats, setStats] = useState({ total: 0, disinfo_count: 0, non_disinfo_count: 0, avg_confidence: 0 });
  const [latest, setLatest] = useState([]);
  const [featureAvgs, setFeatureAvgs] = useState([]);
  const [lastUpdated, setLastUpdated] = useState(new Date().toLocaleTimeString());

  const fetchData = async () => {
    try {
      const [statsRes, latestRes, allRes] = await Promise.all([
        axios.get(`${API_BASE}/stats`),
        axios.get(`${API_BASE}/predictions?limit=5`),
        axios.get(`${API_BASE}/predictions?limit=500`)
      ]);

      setStats(statsRes.data.stats || { total: 0, disinfo_count: 0, non_disinfo_count: 0, avg_confidence: 0 });
      setLatest(latestRes.data.predictions || []);
      
      const data = allRes.data.predictions || [];
      if (data.length > 0) {
        let sums = { cs: 0, urg: 0, part: 0, punc: 0, caps: 0, rep: 0, emo: 0 };
        data.forEach(d => {
          sums.cs += d.code_switching_ratio;
          sums.urg += d.urgency_count;
          sums.part += d.particle_count;
          sums.punc += d.punctuation_intensity;
          sums.caps += d.caps_ratio;
          sums.rep += d.repeated_chars;
          sums.emo += d.emotional_count;
        });
        const n = data.length;
        setFeatureAvgs([
          sums.cs/n, sums.urg/n, sums.part/n, sums.punc/n, 
          sums.caps/n, sums.rep/n, sums.emo/n
        ]);
      }
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.error("Failed to load dashboard data", err);
    }
  };

  useEffect(() => {
    fetchData();
    const iv = setInterval(fetchData, 30000);
    return () => clearInterval(iv);
  }, []);

  const donutData = {
    labels: ['Disinformation', 'Non-Disinformation'],
    datasets: [{
      data: [stats.disinfo_count, stats.non_disinfo_count],
      backgroundColor: ['#ef4444', '#22c55e'],
      borderWidth: 0
    }]
  };

  const barData = {
    labels: ['Code Switching', 'Urgency', 'Particles', 'Punctuation', 'Caps', 'Repeats', 'Emotional'],
    datasets: [{
      label: 'Average Value',
      data: featureAvgs,
      backgroundColor: '#6366f1',
      borderRadius: 4
    }]
  };

  const barOptions = {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    scales: { x: { grid: { color: '#334155' } }, y: { grid: { display: false } } },
    plugins: { legend: { display: false } }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>Dashboard</h1>
        <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Last updated: {lastUpdated}</div>
      </div>

      {/* Stats Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '24px' }}>
        {[
          { icon: Search, label: 'Total Predictions', val: stats.total, color: 'var(--text-secondary)' },
          { icon: AlertTriangle, label: 'Disinformation', val: stats.disinfo_count, color: 'var(--danger)' },
          { icon: CheckCircle, label: 'Non-Disinfo', val: stats.non_disinfo_count, color: 'var(--success)' },
          { icon: BarChart2, label: 'Avg Confidence', val: stats.avg_confidence.toFixed(1)+'%', color: 'var(--accent)' }
        ].map((s, i) => (
          <div key={i} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <s.icon size={16} color={s.color} /> {s.label}
            </div>
            <div style={{ fontSize: '32px', fontWeight: 'bold' }}>{s.val}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
        <div className="card">
          <h2 style={{ fontSize: '16px', marginBottom: '16px' }}>Prediction Distribution</h2>
          <div style={{ height: '250px' }}>
            <Doughnut data={donutData} options={{ maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8' } } } }} />
          </div>
        </div>

        <div className="card" style={{ overflowX: 'auto' }}>
          <h2 style={{ fontSize: '16px', marginBottom: '16px' }}>Latest Predictions</h2>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <th style={{ textAlign: 'left', padding: '12px', color: 'var(--text-secondary)' }}>Text</th>
                <th style={{ textAlign: 'left', padding: '12px', color: 'var(--text-secondary)' }}>Label</th>
                <th style={{ textAlign: 'left', padding: '12px', color: 'var(--text-secondary)' }}>Confidence</th>
                <th style={{ textAlign: 'left', padding: '12px', color: 'var(--text-secondary)' }}>Time</th>
              </tr>
            </thead>
            <tbody>
              {latest.length === 0 ? <tr><td colSpan={4} style={{ textAlign:'center', padding:'20px', color:'var(--text-secondary)' }}>No data yet</td></tr> : 
                latest.map(row => {
                  const isDisinfo = row.label === 'Disinformation';
                  return (
                    <tr key={row.id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '12px', maxWidth: '300px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {row.input_text}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <span className={`badge ${isDisinfo ? 'badge-red' : 'badge-green'}`}>{row.label}</span>
                      </td>
                      <td style={{ padding: '12px' }}>{(row.confidence * 100).toFixed(1)}%</td>
                      <td style={{ padding: '12px', color: 'var(--text-secondary)' }}>
                        {new Date(row.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                      </td>
                    </tr>
                  )
                })
              }
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h2 style={{ fontSize: '16px', marginBottom: '16px' }}>Average Linguistic Feature Values</h2>
        <div style={{ height: '300px' }}>
          <Bar data={barData} options={barOptions} />
        </div>
      </div>
    </div>
  );
}
