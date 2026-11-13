import { useCallback, useEffect, useState } from 'react';
import { api } from '../api.js';
import { Activity, CheckCircle2, Database, GitBranch, Layers3, Server } from 'lucide-react';
import { EmptyState, PageHeader, SectionTitle, StatCard } from '../components/AdminUI.jsx';

export default function Governance() {
  const [activeTab, setActiveTab] = useState('datasets');
  const [datasets, setDatasets] = useState([]);
  const [models, setModels] = useState([]);
  const [runtimeModel, setRuntimeModel] = useState(null);
  const [runs, setRuns] = useState([]);
  const [composition, setComposition] = useState(null);
  const [datasetName, setDatasetName] = useState('');
  const [uploadName, setUploadName] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [busy, setBusy] = useState('');
  const [notice, setNotice] = useState('');
  const [item, setItem] = useState({ version_id: '', candidate_sample_id: '', final_label: 'Misleading', partition_name: 'train', claim_group_id: '' });
  const [error, setError] = useState('');
  const fail = (reason) => setError(reason.response?.data?.detail || reason.message);

  const load = useCallback(() => Promise.all([
    api.get('/dataset-versions'), api.get('/model-versions'), api.get('/training-runs'), api.get('/system-status'),
  ]).then(([datasetResponse, modelResponse, runResponse, statusResponse]) => {
    setDatasets(datasetResponse.data.dataset_versions);
    setModels(modelResponse.data.model_versions);
    setRuns(runResponse.data.training_runs);
    setRuntimeModel(statusResponse.data.model);
  }).catch((reason) => setError(reason.response?.data?.detail || reason.message)), []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!runs.some((row) => ['queued', 'running'].includes(row.status))) return undefined;
    const timer = window.setInterval(load, 5000);
    return () => window.clearInterval(timer);
  }, [load, runs]);

  const createDataset = async (event) => {
    event.preventDefault();
    try { await api.post('/dataset-versions', { version_name: datasetName }); setDatasetName(''); await load(); }
    catch (reason) { fail(reason); }
  };
  const addItem = async (event) => {
    event.preventDefault();
    try { await api.post(`/dataset-versions/${item.version_id}/items`, { ...item, candidate_sample_id: Number(item.candidate_sample_id) }); await load(); }
    catch (reason) { fail(reason); }
  };
  const bulkAdd = async (id) => {
    setBusy(`bulk-${id}`);
    setNotice('');
    try {
      const { data } = await api.post(`/dataset-versions/${id}/items/bulk`);
      setNotice(`Added ${data.added} approved candidates. Train: ${data.partitions.train}, validation: ${data.partitions.validation}, test: ${data.partitions.test}.`);
      await load();
      await viewComposition(id);
    } catch (reason) { fail(reason); }
    finally { setBusy(''); }
  };
  const importDataset = async (event) => {
    event.preventDefault();
    if (!uploadFile) return;
    setBusy('import');
    setNotice('');
    try {
      const form = new FormData();
      form.append('version_name', uploadName);
      form.append('file', uploadFile);
      const { data } = await api.post('/dataset-versions/import', form);
      setNotice(`Imported ${data.imported} validated rows into dataset #${data.dataset_version_id}. Review its composition before approval.`);
      setUploadName('');
      setUploadFile(null);
      await load();
      await viewComposition(data.dataset_version_id);
    } catch (reason) { fail(reason); }
    finally { setBusy(''); }
  };
  const approveDataset = async (id) => {
    try { await api.post(`/dataset-versions/${id}/approve`); await load(); }
    catch (reason) { fail(reason); }
  };
  const viewComposition = async (id) => {
    try { const { data } = await api.get(`/dataset-versions/${id}/composition`); setComposition({ id, ...data }); }
    catch (reason) { fail(reason); }
  };
  const reviewModel = async (id, decision) => {
    try { await api.post(`/model-versions/${id}/review`, { decision }); await load(); }
    catch (reason) { fail(reason); }
  };

  const approvedDatasets = datasets.filter((row) => row.status === 'approved');
  const openRuns = runs.filter((row) => ['queued', 'running'].includes(row.status));

  return <div>
    <PageHeader icon={Layers3} title="Datasets and models" description="Review dataset versions and inspect the historical model registry." />
    <p className="page-context">This deployment uses only the verified model_4 hybrid classifier. Training, model registration and switching are disabled. Dataset review remains available.</p>
    {error && <p style={{ color: 'var(--danger)', marginTop: 12 }}>{error}</p>}
    {notice && <p className="notice-success">{notice}</p>}

    <section className="card dashboard-section">
      <div className="summary-grid">
        <StatCard icon={Database} value={datasets.length} label="Dataset versions" />
        <StatCard icon={CheckCircle2} value={approvedDatasets.length} label="Approved datasets" tone="green" />
        <StatCard icon={Activity} value={openRuns.length} label="Open training runs" tone="amber" />
        <StatCard icon={Server} value={runtimeModel?.ready ? runtimeModel.training_run_id : 'Unavailable'} label="Active model" />
      </div>
    </section>

    <nav className="tab-bar" aria-label="Dataset and model sections">
      <button className={`tab-button ${activeTab === 'datasets' ? 'active' : ''}`} onClick={() => setActiveTab('datasets')}><Database size={16} />Dataset versions</button>
      <button className={`tab-button ${activeTab === 'models' ? 'active' : ''}`} onClick={() => setActiveTab('models')}><GitBranch size={16} />Model versions</button>
    </nav>

    {activeTab === 'datasets' && <>
      <section className="card">
        <SectionTitle icon={Database} title="Dataset versions" description="Only evidence-verified and approved candidates may become dataset members." actions={<form onSubmit={createDataset} className="inline-form"><input required placeholder="New version name" value={datasetName} onChange={(event) => setDatasetName(event.target.value)}/><button className="btn-primary">Create version</button></form>} />
        <div className="table-wrap"><table><thead><tr><th>ID</th><th>Version</th><th>Status</th><th>Actions</th></tr></thead><tbody>
          {datasets.length ? datasets.map((row) => <tr key={row.dataset_version_id}><td>#{row.dataset_version_id}</td><td>{row.version_name}</td><td>{row.status}</td><td><div className="row-actions"><button className="ghost-btn" onClick={() => viewComposition(row.dataset_version_id)}>View composition</button>{row.status === 'draft' && <><button className="ghost-btn" disabled={Boolean(busy)} onClick={() => bulkAdd(row.dataset_version_id)}>{busy === `bulk-${row.dataset_version_id}` ? 'Adding…' : 'Add approved candidates'}</button><button className="ghost-btn" onClick={() => approveDataset(row.dataset_version_id)}>Approve</button></>}</div></td></tr>) : <tr><td colSpan="4"><EmptyState icon={Database} title="No dataset versions yet" description="Create a version to start an evidence-reviewed dataset." /></td></tr>}
        </tbody></table></div>
      </section>

      <details className="card advanced-panel" style={{ marginTop: 18 }}><summary>Import an externally validated CSV or Excel dataset</summary><p>Required columns: text, label, topic, evidence_url, and claim_group_id. Optional partition_name values are train, validation, or test; missing partitions are assigned deterministically by claim group.</p><form onSubmit={importDataset} className="advanced-form"><input required placeholder="New dataset version name" value={uploadName} onChange={(event) => setUploadName(event.target.value)}/><input required type="file" accept=".csv,.xlsx" onChange={(event) => setUploadFile(event.target.files?.[0] || null)}/><button className="btn-primary" disabled={busy === 'import'}>{busy === 'import' ? 'Importing…' : 'Import validated dataset'}</button></form></details>

      {composition && <section className="card dashboard-section"><SectionTitle icon={Layers3} title={`Dataset #${composition.id} composition`} description={`Targets: ${composition.targets.total_taglish} Taglish, ${composition.targets.per_class} per class, ${composition.targets.per_topic} per topic, and ${composition.targets.per_topic_class} per class/topic.`} /><div className="table-wrap"><table><thead><tr><th>Language</th><th>Topic</th><th>Label</th><th>Partition</th><th>Count</th></tr></thead><tbody>{composition.composition.length ? composition.composition.map((row, index) => <tr key={`${row.topic}-${row.final_label}-${row.partition_name}-${index}`}><td>{row.language}</td><td>{row.topic}</td><td>{row.final_label}</td><td>{row.partition_name}</td><td>{row.sample_count}</td></tr>) : <tr><td colSpan="5"><EmptyState icon={Layers3} title="No approved members yet" description="Approved dataset members will appear here." /></td></tr>}</tbody></table></div></section>}

      <details className="card advanced-panel" style={{ marginTop: 18 }}><summary>Advanced: add an approved candidate to a dataset</summary><p>Use this only after evidence and candidate review are complete. Claim groups must stay within one partition.</p><form onSubmit={addItem} className="advanced-form"><input required placeholder="Dataset version ID" value={item.version_id} onChange={(event) => setItem({ ...item, version_id: event.target.value })}/><input required placeholder="Approved candidate ID" value={item.candidate_sample_id} onChange={(event) => setItem({ ...item, candidate_sample_id: event.target.value })}/><input required placeholder="Claim group ID" value={item.claim_group_id} onChange={(event) => setItem({ ...item, claim_group_id: event.target.value })}/><select value={item.final_label} onChange={(event) => setItem({ ...item, final_label: event.target.value })}><option>Misleading</option><option>Non-Misleading</option></select><select value={item.partition_name} onChange={(event) => setItem({ ...item, partition_name: event.target.value })}><option value="train">Train</option><option value="validation">Validation</option><option value="test">Test</option></select><button className="btn-primary">Add to dataset</button></form></details>
    </>}

    {activeTab === 'models' && <>
      <section className="card"><SectionTitle icon={GitBranch} title="Historical model registry" description="These records do not select the running classifier. The active runtime is shown above." /><div className="table-wrap"><table><thead><tr><th>Version</th><th>Dataset</th><th>Mode</th><th>Status</th><th>Metrics</th><th>Actions</th></tr></thead><tbody>{models.length ? models.map((row) => <tr key={row.model_version_id}><td>{row.version_name}<br/><small>{row.model_name}</small></td><td>#{row.dataset_version_id}</td><td>{row.feature_mode}</td><td>{row.status}</td><td><small>{JSON.stringify(row.metrics)}</small></td><td><div className="row-actions">{row.status === 'candidate' && <><button className="btn-primary" onClick={() => reviewModel(row.model_version_id, 'approved')}>Approve</button><button className="ghost-btn" onClick={() => reviewModel(row.model_version_id, 'rejected')}>Reject</button></>}</div></td></tr>) : <tr><td colSpan="6"><EmptyState icon={GitBranch} title="No model versions" description="Historical model versions will appear here when available." /></td></tr>}</tbody></table></div></section>

      <section className="card dashboard-section"><SectionTitle icon={Activity} title="Training runs" description="Queued and running jobs refresh automatically every five seconds." />{runs.length ? <div className="table-wrap"><table><thead><tr><th>ID</th><th>Requested version</th><th>Status</th><th>Progress</th><th>Result</th></tr></thead><tbody>{runs.map((run) => <tr key={run.training_run_id}><td>#{run.training_run_id}</td><td>{run.requested_version_name}</td><td>{run.status}</td><td style={{ minWidth: 220 }}><div className="progress-track"><span style={{ width: `${run.progress_percent || 0}%` }}/></div><small>{run.progress_percent || 0}% · {run.progress_stage || 'Queued'}</small></td><td>{run.error_message || (run.model_version_id ? `Model #${run.model_version_id}` : '—')}</td></tr>)}</tbody></table></div> : <EmptyState icon={Activity} title="No training runs" description="Historical run activity will appear here when available." />}</section>

    </>}
  </div>;
}
