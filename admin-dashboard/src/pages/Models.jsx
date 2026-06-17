import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Chart as ChartJS, RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend } from 'chart.js';
import { Radar } from 'react-chartjs-2';

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

const API_BASE = 'http://localhost:8000/admin-api';

export default function Models() {
  const [latest, setLatest] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    Promise.all([
      axios.get(`${API_BASE}/models/latest`),
      axios.get(`${API_BASE}/models`)
    ]).then(([resL, resH]) => {
      if (!resL.data.error) setLatest(resL.data.model);
      if (!resH.data.error) setHistory(resH.data.models || []);
    }).catch(err => console.error(err));
  }, []);

  const getInterp = (val) => {
    if (val >= 90) return { label: 'Excellent', color: 'var(--success)' };
    if (val >= 80) return { label: 'Very Good', color: 'var(--accent)' };
    if (val >= 70) return { label: 'Good', color: 'var(--warning)' };
    if (val >= 60) return { label: 'Fair', color: 'var(--orange)' };
    return { label: 'Poor', color: 'var(--danger)' };
  };

  const radarData = {
    labels: ['Accuracy', 'Precision', 'Recall', 'F1 Score'],
    datasets: [{
      label: 'Latest Model',
      data: latest ? [latest.accuracy*100, latest.precision_macro*100, latest.recall_macro*100, latest.f1_macro*100] : [0,0,0,0],
      backgroundColor: 'rgba(99, 102, 241, 0.3)',
      borderColor: '#6366f1',
      pointBackgroundColor: '#ffffff',
      borderWidth: 2
    }]
  };

  const radarOptions = {
    responsive: true, maintainAspectRatio: false,
    scales: {
      r: {
        angleLines: { color: '#334155' },
        grid: { color: '#334155' },
        pointLabels: { color: '#94a3b8', font: { size: 12 } },
        ticks: { display: false, min: 0, max: 100 }
      }
    },
    plugins: { legend: { display: false } }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>Model Performance</h1>

      {latest && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gridTemplateRows: 'repeat(2, 1fr)', gap: '16px' }}>
            {[
              { label: 'Accuracy', val: latest.accuracy*100, isMs: false },
              { label: 'Precision (Macro)', val: latest.precision_macro*100, isMs: false },
              { label: 'Recall (Macro)', val: latest.recall_macro*100, isMs: false },
              { label: 'F1-Score (Macro)', val: latest.f1_macro*100, isMs: false },
              { label: 'Avg Inference Time', val: latest.avg_inference_ms, isMs: true },
              { 
                label: 'HYBRID MODEL', 
                val: 'ACTIVE', 
                isText: true,
                subText: `AVG PERFORMANCE: ${((latest.accuracy + latest.precision_macro + latest.recall_macro + latest.f1_macro) / 4 * 100).toFixed(2)}%`
              }
            ].map((s, i) => {
              const interp = (!s.isMs && !s.isText) ? getInterp(s.val) : null;
              return (
                <div key={i} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '6px', borderLeft: interp ? `4px solid ${interp.color}` : '1px solid var(--border)' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    {s.label}
                  </div>
                  <div style={{ fontSize: '22px', fontWeight: 'bold', color: s.isMs ? 'var(--accent)' : 'white', lineHeight: '1.2' }}>
                    {s.isText ? s.val : `${s.val.toFixed(2)}${s.isMs ? ' ms' : '%'}`}
                  </div>
                  {s.subText && <div style={{ fontSize: '14px', color: 'var(--accent)', marginTop: '4px', fontWeight: '900', letterSpacing: '0.5px' }}>{s.subText}</div>}
                  {interp && <div style={{ fontSize: '10px', fontWeight: 'bold', color: interp.color, textTransform: 'uppercase' }}>{interp.label}</div>}
                </div>
              )
            })}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '24px' }}>
            <div className="card">
              <h2 style={{ fontSize: '16px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent)' }}></span>
                Performance Balance (Radar)
              </h2>
              <div style={{ height: '350px' }}><Radar data={radarData} options={radarOptions} /></div>
            </div>

            <div className="card">
              <h2 style={{ fontSize: '16px', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--success)' }}></span>
                Confusion Matrix (Validation Proof)
              </h2>
              <div style={{ display: 'grid', gridTemplateColumns: '80px 1fr 1fr', gap: '8px', textAlign: 'center' }}>
                <div />
                <div style={{ padding: '8px', fontSize: '10px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Predicted: Non</div>
                <div style={{ padding: '8px', fontSize: '10px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Predicted: Disinfo</div>
                
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', color: 'var(--text-secondary)', textTransform: 'uppercase', writingMode: 'vertical-lr', transform: 'rotate(180deg)' }}>Actual</div>
                
                <div style={{ display: 'grid', gridTemplateRows: '1fr 1fr', gap: '8px', gridColumn: '2 / span 2' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                    <div style={{ padding: '20px 10px', backgroundColor: 'rgba(34, 197, 94, 0.05)', borderRadius: '8px', border: '1px solid rgba(34, 197, 94, 0.2)' }}>
                      <div style={{ fontSize: '20px', fontWeight: 'bold', color: 'var(--success)' }}>{latest.conf_tn}</div>
                      <div style={{ fontSize: '9px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>True Negatives</div>
                    </div>
                    <div style={{ padding: '20px 10px', backgroundColor: 'rgba(239, 68, 68, 0.05)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                      <div style={{ fontSize: '20px', fontWeight: 'bold', color: 'var(--danger)' }}>{latest.conf_fp}</div>
                      <div style={{ fontSize: '9px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>False Positives</div>
                    </div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                    <div style={{ padding: '20px 10px', backgroundColor: 'rgba(239, 68, 68, 0.05)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                      <div style={{ fontSize: '20px', fontWeight: 'bold', color: 'var(--danger)' }}>{latest.conf_fn}</div>
                      <div style={{ fontSize: '9px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>False Negatives</div>
                    </div>
                    <div style={{ padding: '20px 10px', backgroundColor: 'rgba(34, 197, 94, 0.05)', borderRadius: '8px', border: '1px solid rgba(34, 197, 94, 0.2)' }}>
                      <div style={{ fontSize: '20px', fontWeight: 'bold', color: 'var(--success)' }}>{latest.conf_tp}</div>
                      <div style={{ fontSize: '9px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>True Positives</div>
                    </div>
                  </div>
                </div>
              </div>
              <p style={{ marginTop: '20px', fontSize: '11px', color: 'var(--text-secondary)', textAlign: 'center', fontStyle: 'italic' }}>
                * This matrix confirms the model's ability to distinguish between classes without bias.
              </p>
            </div>
          </div>
        </>
      )}

    </div>
  );
}
