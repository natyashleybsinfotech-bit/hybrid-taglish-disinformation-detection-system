import { useEffect, useState } from 'react';
import { Activity, Cpu, GitBranch, Gauge, ShieldCheck, Timer, TrendingUp } from 'lucide-react';
import { Chart as ChartJS, Filler, LineElement, PointElement, RadarController, RadialLinearScale, Tooltip } from 'chart.js';
import { Radar } from 'react-chartjs-2';
import { api } from '../api.js';
import { EmptyState, HashCopy, PageHeader, SectionTitle, StatusBadge } from '../components/AdminUI.jsx';

ChartJS.register(RadarController, RadialLinearScale, PointElement, LineElement, Filler, Tooltip);

// Saved held-out evaluation for the original model_4 run (20261011T235112Z).
// Sources: backend-api/models/TRAINING RESULTS/records/test_metrics_with_cluster_bootstrap.csv
//          backend-api/models/TRAINING RESULTS/records/inference_latency.csv
const heldOutMetrics = [
  { label: 'Accuracy', value: '93.65%', tag: 'EXCELLENT', tone: 'indigo', icon: ShieldCheck },
  { label: 'Macro F1', value: '93.64%', tag: 'EXCELLENT', tone: 'violet', icon: TrendingUp },
  { label: 'False positive rate', value: '2.67%', tag: 'LOW', tone: 'green', icon: Gauge },
  { label: 'Median latency', value: '22.28 ms', tag: 'FAST', tone: 'cyan', icon: Timer },
];

const confusion = { tn: 292, fp: 8, fn: 30, tp: 268 };
const macroPrecision = ((confusion.tn / (confusion.tn + confusion.fn)) + (confusion.tp / (confusion.tp + confusion.fp))) * 50;
const macroRecall = ((confusion.tn / (confusion.tn + confusion.fp)) + (confusion.tp / (confusion.tp + confusion.fn))) * 50;
const radarData = {
  labels: ['Accuracy', 'Precision', 'Recall', 'F1 score'],
  datasets: [{ data: [93.65, macroPrecision, macroRecall, 93.64], borderColor: '#818cf8', backgroundColor: 'rgba(99, 102, 241, .27)', pointBackgroundColor: '#c7d2fe', pointBorderColor: '#6366f1', pointBorderWidth: 2, pointRadius: 4, pointHoverRadius: 6, borderWidth: 2, fill: true }],
};
const radarOptions = {
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 450 },
  plugins: { legend: { display: false }, tooltip: { callbacks: { label: ({ parsed }) => `${parsed.r.toFixed(2)}%` } } },
  scales: { r: { min: 0, max: 100, angleLines: { color: 'rgba(148, 163, 184, .19)' }, grid: { color: 'rgba(148, 163, 184, .19)', circular: false }, pointLabels: { color: '#cbd5e1', font: { size: 12, weight: '600' }, padding: 14 }, ticks: { display: false, stepSize: 20 }, backgroundColor: 'transparent' } },
};

function MetricCard({ label, value, tag, tone, icon: Icon }) {
  return <div className={`performance-metric performance-metric-${tone}`}>
    <div className="performance-metric-top"><span>{label}</span><Icon size={19} aria-hidden="true" /></div>
    <strong>{value}</strong><small>{tag}</small>
  </div>;
}

export default function Performance() {
  const [models, setModels] = useState([]);
  const [error, setError] = useState('');
  useEffect(() => {
    api.get('/model-versions').then(({ data }) => setModels(data.model_versions)).catch((reason) => setError(reason.response?.data?.detail || reason.message));
  }, []);
  return <div>
    <PageHeader icon={Activity} title="Model performance" description="Read-only runtime identity and historical quality information. Dataset and retraining controls are not available here." />
    {error && <p className="error-card">{error}</p>}
    <section className="card dashboard-section" data-paper-model="original-hybrid">
      <SectionTitle icon={Cpu} title="Research model" description="Original hybrid model documented in the paper." />
      <div className="detail-list">
        <div><span>Classifier</span><strong>Hybrid DistilBERT + linguistic features + Logistic Regression</strong></div>
        <div><span>Feature set</span><strong>768 contextual + 7 linguistic features</strong></div>
        <div><span>Training run</span><strong>20261011T235112Z</strong></div>
        <div><span>Decision threshold</span><strong>0.65</strong></div>
        <div><span>Artifact SHA-256</span><HashCopy value="72d87971ee2af7fca1f6f0a9b94bbe92618bd92ce8c5e48e35b80882e1321c7c" /></div>
      </div>
      <p className="muted-copy">Saved research model and evaluation results. Current operational details are available in System status.</p>
    </section>
    <div className="performance-evaluation" aria-label="Saved held-out evaluation for original model 4">
      <div className="performance-evaluation-head"><div><h2>Historical held-out test evaluation</h2><p>Original hybrid model_4 · 775 features · 598 samples</p></div><span className="performance-evaluation-run">Run 20261011T235112Z</span></div>
      <p className="info-note">These saved results evaluate the original hybrid model against inherited dataset labels. They do not measure the current external AI classifier, evidence decisions, or real-world Facebook accuracy.</p>
      <div className="performance-metrics">{heldOutMetrics.map((metric) => <MetricCard key={metric.label} {...metric} />)}</div>
      <div className="performance-visuals">
      <div className="card performance-radar-panel"><div className="performance-matrix-heading"><h3><span className="performance-panel-dot" />Performance balance</h3><span>Macro averages</span></div>
        <div className="performance-radar-chart"><Radar data={radarData} options={radarOptions} role="img" aria-label={`Radar chart: accuracy 93.65 percent, macro precision ${macroPrecision.toFixed(2)} percent, macro recall ${macroRecall.toFixed(2)} percent, macro F1 score 93.64 percent`} /></div>
        <p className="performance-radar-note">Precision {macroPrecision.toFixed(2)}% · Recall {macroRecall.toFixed(2)}% · calculated from the confusion matrix</p>
      </div>
      <div className="card performance-matrix-panel"><div className="performance-matrix-heading"><h3><span className="performance-panel-dot green" />Confusion matrix</h3><span>598 held-out samples</span></div>
        <div className="performance-matrix-scroll"><table className="performance-matrix"><thead><tr><th scope="col">Actual / Predicted</th><th scope="col">Non-Misleading</th><th scope="col">Misleading</th></tr></thead><tbody>
          <tr><th scope="row">Non-Misleading</th><td className="matrix-correct"><strong>{confusion.tn}</strong><span>True negatives</span></td><td className="matrix-error"><strong>{confusion.fp}</strong><span>False positives</span></td></tr>
          <tr><th scope="row">Misleading</th><td className="matrix-error"><strong>{confusion.fn}</strong><span>False negatives</span></td><td className="matrix-correct"><strong>{confusion.tp}</strong><span>True positives</span></td></tr>
        </tbody></table></div>
      </div>
      </div>
    </div>
    <section className="card dashboard-section"><SectionTitle icon={GitBranch} title="Model versions" description="Historical registry and evaluation metrics." />
      <div className="table-wrap"><table><thead><tr><th>Version</th><th>Status</th><th>Dataset</th><th>Evaluation metrics</th></tr></thead><tbody>{models.length ? models.map((model) => <tr key={model.model_version_id}><td><strong>{model.version_name}</strong><br/><small>{model.model_name}</small></td><td><StatusBadge value={model.status} /></td><td>#{model.dataset_version_id}</td><td><pre className="metrics-json">{JSON.stringify(model.metrics, null, 2)}</pre></td></tr>) : <tr><td colSpan="4"><EmptyState icon={GitBranch} title="No model versions registered" description="Historical versions will appear here when available." /></td></tr>}</tbody></table></div>
    </section>
  </div>;
}
