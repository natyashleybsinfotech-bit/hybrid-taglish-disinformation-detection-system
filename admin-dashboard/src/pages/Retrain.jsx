import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000/admin-api';

export default function Retrain() {
  const [latest, setLatest]         = useState(null);
  const [status, setStatus]         = useState({ running: false, message: 'Idle' });
  const [logs, setLogs]             = useState([]);
  const [retrainMode, setRetrainMode] = useState(null); // 'dashboard' | 'uploaded'

  // Upload state
  const [uploadFile, setUploadFile]     = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null); // { filename, size_bytes } or null
  const [uploading, setUploading]       = useState(false);
  const [uploadMsg, setUploadMsg]       = useState('');

  const pollRef   = useRef(null);
  const logEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // ── Load model info + existing upload status on mount ──
  useEffect(() => {
    axios.get(`${API_BASE}/models/latest`)
      .then(res => { if (!res.data.error) setLatest(res.data.model); })
      .catch(() => {});
    axios.get(`${API_BASE}/upload-dataset/status`)
      .then(res => { if (res.data.has_upload) setUploadStatus(res.data); })
      .catch(() => {});
    checkStatus();
    return () => clearInterval(pollRef.current);
  }, []);

  // ── Log helpers ──
  const appendLog = (msg) => {
    setLogs(prev => {
      if (prev.length > 0 && prev[prev.length - 1].msg === msg) return prev;
      return [...prev, { time: new Date().toLocaleTimeString([], { hour12: false }), msg }];
    });
    setTimeout(() => {
      if (logEndRef.current) logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  // ── Poll retrain status ──
  const checkStatus = async () => {
    try {
      const res = await axios.get(`${API_BASE}/retrain/status`);
      setStatus(res.data);
      if (res.data.message && res.data.message !== 'Idle') appendLog(res.data.message);
      if (res.data.running) {
        if (!pollRef.current) pollRef.current = setInterval(checkStatus, 3000);
      } else {
        clearInterval(pollRef.current);
        pollRef.current = null;
        if (res.data.message?.toLowerCase().includes('complete')) {
          axios.get(`${API_BASE}/models/latest`).then(r => {
            if (!r.data.error) setLatest(r.data.model);
          }).catch(() => {});
        }
      }
    } catch { /* ignore */ }
  };

  // ── Retrain: dashboard data ──
  const handleRetrainDashboard = async () => {
    setLogs([]);
    setRetrainMode('dashboard');
    appendLog('Initiating retrain with dashboard data...');
    try {
      const res = await axios.post(`${API_BASE}/retrain`);
      appendLog(res.data.message || 'Retraining started...');
      setStatus({ running: true, message: res.data.message });
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(checkStatus, 3000);
    } catch (err) {
      appendLog('Failed: ' + (err.response?.data?.detail || err.message));
    }
  };

  // ── Retrain: uploaded dataset ──
  const handleRetrainUploaded = async () => {
    if (!uploadStatus?.filename) {
      setUploadMsg('⚠ Please upload a dataset CSV first.');
      return;
    }
    setLogs([]);
    setRetrainMode('uploaded');
    appendLog(`Initiating retrain with uploaded dataset: ${uploadStatus.filename}`);
    try {
      const res = await axios.post(`${API_BASE}/retrain-uploaded`);
      appendLog(res.data.message || 'Retraining started...');
      setStatus({ running: true, message: res.data.message });
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(checkStatus, 3000);
    } catch (err) {
      appendLog('Failed: ' + (err.response?.data?.detail || err.message));
    }
  };

  // ── File upload ──
  const handleFileChange = (e) => {
    const f = e.target.files[0];
    if (f && f.name.endsWith('.csv')) {
      setUploadFile(f);
      setUploadMsg('');
    } else {
      setUploadFile(null);
      setUploadMsg('⚠ Only CSV files are accepted.');
    }
  };

  const handleUpload = async () => {
    if (!uploadFile) { setUploadMsg('⚠ Please select a CSV file first.'); return; }
    setUploading(true);
    setUploadMsg('Uploading...');
    const formData = new FormData();
    formData.append('file', uploadFile);
    try {
      const res = await axios.post(`${API_BASE}/upload-dataset`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setUploadStatus({ filename: res.data.filename, size_bytes: res.data.size_bytes });
      setUploadMsg('');
      setUploadFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err) {
      setUploadMsg('Upload failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setUploading(false);
    }
  };

  const getInterp = (val) => {
    if (val >= 90) return { label: 'Excellent', color: 'var(--success)' };
    if (val >= 80) return { label: 'Very Good', color: 'var(--accent)' };
    if (val >= 70) return { label: 'Good', color: 'var(--warning)' };
    if (val >= 60) return { label: 'Fair', color: 'var(--orange)' };
    return { label: 'Poor', color: 'var(--danger)' };
  };

  const fmtBytes = (b) => b > 1024 * 1024 ? `${(b / 1024 / 1024).toFixed(2)} MB` : `${(b / 1024).toFixed(1)} KB`;

  const isRunning = status.running;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '900px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>Retrain Model</h1>

      {/* ── Active Model ── */}
      <div className="card">
        <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '16px' }}>Active Model</h2>
        {!latest ? (
          <div style={{ color: 'var(--text-secondary)' }}>Loading...</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            {[
              { label: 'Model Name', val: latest.model_name },
              { label: 'Model Type', val: <span style={{ color: 'var(--text-secondary)' }}>{latest.model_type}</span> },
              { label: 'Accuracy', val: <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>{(latest.accuracy * 100).toFixed(2)}% <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 'bold', textTransform: 'uppercase', color: 'white', backgroundColor: getInterp(latest.accuracy * 100).color }}>{getInterp(latest.accuracy * 100).label}</span></div> },
              { label: 'F1 Score', val: <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>{(latest.f1_macro * 100).toFixed(2)}% <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 'bold', textTransform: 'uppercase', color: 'white', backgroundColor: getInterp(latest.f1_macro * 100).color }}>{getInterp(latest.f1_macro * 100).label}</span></div> },
              { label: 'Avg Inference', val: `${latest.avg_inference_ms.toFixed(2)} ms` },
              { label: 'Trained At', val: <span style={{ color: 'var(--text-secondary)' }}>{new Date(latest.trained_at).toLocaleString()}</span> },
            ].map((item, i) => (
              <div key={i} style={{ backgroundColor: 'var(--bg-page)', border: '1px solid var(--border)', padding: '12px 16px', borderRadius: '8px' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '4px' }}>{item.label}</div>
                <div style={{ fontSize: '15px', fontWeight: 'bold' }}>{item.val}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Upload Dataset ── */}
      <div className="card">
        <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '4px' }}>
          Upload Cleaned &amp; Preprocessed Dataset
        </h2>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px', lineHeight: 1.5 }}>
          Upload a cleaned and preprocessed CSV file (<code>text</code> and <code>label</code> columns required).
          This dataset will be used for the <strong>Retrain with Uploaded Dataset</strong> option below.
        </p>

        {/* Current upload status */}
        {uploadStatus?.filename && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', backgroundColor: 'rgba(34,197,94,0.08)', border: '1px solid var(--success)', borderRadius: '8px', padding: '10px 14px', marginBottom: '16px', fontSize: '13px' }}>
            <span style={{ fontSize: '18px' }}>📄</span>
            <div>
              <div style={{ fontWeight: 'bold', color: 'var(--success)' }}>Dataset Ready</div>
              <div style={{ color: 'var(--text-secondary)' }}>{uploadStatus.filename} &nbsp;·&nbsp; {fmtBytes(uploadStatus.size_bytes)}</div>
            </div>
          </div>
        )}

        {/* File picker */}
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            style={{
              flex: 1,
              padding: '9px 12px',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              backgroundColor: 'var(--bg-page)',
              color: 'var(--text-primary)',
              fontSize: '13px',
              cursor: 'pointer',
            }}
          />
          <button
            className="btn-primary"
            style={{ height: '40px', padding: '0 20px', fontSize: '13px', whiteSpace: 'nowrap', opacity: uploading ? 0.6 : 1 }}
            onClick={handleUpload}
            disabled={uploading || !uploadFile}
          >
            {uploading ? 'Uploading...' : '⬆ Upload Dataset'}
          </button>
        </div>

        {uploadFile && !uploading && (
          <div style={{ marginTop: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
            Selected: <strong>{uploadFile.name}</strong> ({fmtBytes(uploadFile.size)})
          </div>
        )}
        {uploadMsg && (
          <div style={{ marginTop: '8px', fontSize: '13px', color: uploadMsg.startsWith('⚠') ? 'var(--warning)' : 'var(--danger)' }}>
            {uploadMsg}
          </div>
        )}
      </div>

      {/* ── Retrain ── */}
      <div className="card">
        <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '4px' }}>
          Trigger Retraining
        </h2>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '16px' }}>
          Choose how to retrain the hybrid model. Retraining re-extracts DistilBERT embeddings, applies SMOTE,
          retrains the Logistic Regression classifier, saves the updated model, and reloads it live.
          This may take <strong>10–30 minutes</strong>.
        </p>

        <div style={{ backgroundColor: 'rgba(245,158,11,0.1)', borderLeft: '3px solid var(--warning)', padding: '10px 14px', color: 'var(--warning)', fontSize: '13px', marginBottom: '24px', borderRadius: '0 8px 8px 0' }}>
          The prediction endpoint continues using the current model during retraining. The new model activates only after completion.
        </div>

        {/* Two retrain buttons */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>

          {/* Button 1: Dashboard data */}
          <div style={{ border: '1px solid var(--border)', borderRadius: '12px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px', backgroundColor: 'var(--bg-page)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '24px' }}>🗄️</span>
              <div>
                <div style={{ fontWeight: 'bold', fontSize: '14px' }}>Retrain with Dashboard Data</div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>Uses the original dataset loaded into the system</div>
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ width: '100%', height: '44px', fontSize: '14px', opacity: isRunning ? 0.6 : 1 }}
              onClick={handleRetrainDashboard}
              disabled={isRunning}
            >
              {isRunning && retrainMode === 'dashboard' ? '⟳ Retraining...' : '▶ Start (Dashboard Data)'}
            </button>
          </div>

          {/* Button 2: Uploaded dataset */}
          <div style={{ border: `1px solid ${uploadStatus?.filename ? 'var(--accent)' : 'var(--border)'}`, borderRadius: '12px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px', backgroundColor: 'var(--bg-page)', position: 'relative' }}>
            {uploadStatus?.filename && (
              <div style={{ position: 'absolute', top: '10px', right: '10px', fontSize: '10px', fontWeight: 'bold', backgroundColor: 'var(--accent)', color: 'white', padding: '2px 8px', borderRadius: '99px', textTransform: 'uppercase' }}>
                Dataset Ready
              </div>
            )}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '24px' }}>📂</span>
              <div>
                <div style={{ fontWeight: 'bold', fontSize: '14px' }}>Retrain with Uploaded Dataset</div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  {uploadStatus?.filename
                    ? `Using: ${uploadStatus.filename}`
                    : 'Upload a dataset in Step 1 first'}
                </div>
              </div>
            </div>
            <button
              className="btn-primary"
              style={{ width: '100%', height: '44px', fontSize: '14px', opacity: (isRunning || !uploadStatus?.filename) ? 0.5 : 1, background: uploadStatus?.filename ? undefined : 'var(--border)', color: uploadStatus?.filename ? undefined : 'var(--text-secondary)', cursor: uploadStatus?.filename ? 'pointer' : 'not-allowed' }}
              onClick={handleRetrainUploaded}
              disabled={isRunning || !uploadStatus?.filename}
            >
              {isRunning && retrainMode === 'uploaded' ? '⟳ Retraining...' : '▶ Start (Uploaded Dataset)'}
            </button>
          </div>

        </div>

        {/* Progress bar */}
        {isRunning && (
          <div style={{ height: '6px', width: '100%', backgroundColor: 'var(--border)', borderRadius: '3px', overflow: 'hidden', marginTop: '20px', position: 'relative' }}>
            <div style={{ height: '100%', width: '30%', background: 'linear-gradient(90deg, transparent, var(--accent), transparent)', animation: 'slide 1.5s infinite linear', position: 'absolute' }} />
            <style>{`@keyframes slide { 0% { left: -30%; } 100% { left: 100%; } }`}</style>
          </div>
        )}

        {/* Log console */}
        {logs.length > 0 && (
          <div style={{ backgroundColor: 'var(--bg-page)', border: '1px solid var(--border)', borderRadius: '8px', padding: '12px', fontFamily: 'monospace', fontSize: '12px', color: 'var(--text-secondary)', maxHeight: '160px', overflowY: 'auto', marginTop: '16px' }}>
            {logs.map((log, i) => (
              <div key={i} style={{ marginBottom: '4px' }}>
                <span style={{ color: 'var(--accent)', marginRight: '8px' }}>[{log.time}]</span>
                {log.msg}
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        )}

        {/* Final result */}
        {!isRunning && logs.length > 0 && (
          <div style={{
            marginTop: '16px', padding: '14px', borderRadius: '8px', fontSize: '14px', fontWeight: 'bold',
            backgroundColor: status.message?.toLowerCase().includes('complete') ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
            color: status.message?.toLowerCase().includes('complete') ? 'var(--success)' : '#fca5a5',
            border: `1px solid ${status.message?.toLowerCase().includes('complete') ? 'var(--success)' : 'var(--danger)'}`,
          }}>
            {status.message}
          </div>
        )}
      </div>
    </div>
  );
}
