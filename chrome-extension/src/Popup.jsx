import React, { useEffect, useRef, useState } from 'react';
import { analyzeMedia, analyzeText } from './api.js';

const EMPTY_PAGE = { url: '', title: '' };
const safeUrl = value => { try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) ? url.href : null; } catch { return null; } };
export function Result({ result }) {
  if (!result) return null;
  const retrieval = result.retrieval_status;
  const noSources = retrieval === 'not_requested' ? 'Related-source lookup was not requested.' : retrieval === 'no_results' ? 'No matching links were returned from the allowed publishers.' : 'Related-source lookup is unavailable. The prediction is unchanged.';
  const factChecks = result.fact_check_status;
  const noFactChecks = factChecks === 'not_requested' ? 'Published fact-check lookup was not requested.' : factChecks === 'no_results' ? 'Google Fact Check returned no matching published reviews.' : 'Published fact-check lookup is unavailable. The prediction is unchanged.';
  return <section className="result-stack" aria-label="Analysis result">
    <article className="result-card prediction-card">
      <p className="eyebrow">MODEL PREDICTION</p><h2>{result.internal_label}</h2>
      <p className="score"><strong>{result.model_score > .99995 && result.model_score < 1 ? '>99.99' : result.model_score > 0 && result.model_score < .00005 ? '<0.01' : (result.model_score * 100).toFixed(2)}%</strong> Misleading-class score</p>
      <p>This score is the model output for the Misleading class. Scores of 65% or above predict Misleading. It is not calibrated certainty or a factual verdict.</p>
      {result.model_scope_notice && <p className="notice">{result.model_scope_notice}</p>}
    </article>
    <details className="result-card"><summary>Seven measured text signals</summary>
      <p>Measurements from this input, before scaling. These are not feature contributions or proof that a claim is false. A zero denominator produces 0.</p>
      <dl className="feature-list">{result.linguistic_indicators?.map(item => <div key={item.name} data-feature={item.name} data-value={item.value}>
        <dt>{item.display_name || item.name.replaceAll('_', ' ')} <strong>{Number(item.value).toFixed(4)} ratio</strong></dt>
        <dd>{item.definition}</dd>
      </div>)}</dl>
    </details>
    <section className="result-card"><h3>Related reading</h3><p>Links are search results, not automatically supporting or refuting evidence. Review the original claim, date and context.</p>
      {!result.related_sources?.length && <p className="notice">{noSources} Missing links do not validate the prediction.</p>}
      {result.related_sources?.filter(source => safeUrl(source.url)).map(source => <article className="source" key={source.url}>
        <a href={safeUrl(source.url)} target="_blank" rel="noopener noreferrer">{source.title}</a>
        <p>{source.source || 'Publisher not supplied'} · Search result{source.date ? ` · ${source.date}` : ''}</p>
      </article>)}
    </section>
    <section className="result-card"><h3>Published fact-check reviews</h3><p>These are independent Google Fact Check search matches. Their ratings do not set or change the SuriPH model prediction.</p>
      {!result.fact_check_matches?.length && <p className="notice">{noFactChecks}</p>}
      {result.fact_check_matches?.filter(match => safeUrl(match.url)).map(match => <article className="source" key={match.url}>
        <a href={safeUrl(match.url)} target="_blank" rel="noopener noreferrer">{match.title || match.claim}</a>
        <p>{match.publisher || 'Publisher not supplied'}{match.rating ? ` · Published rating: ${match.rating}` : ''}{match.review_date ? ` · ${match.review_date}` : ''}</p>
      </article>)}
    </section>
    <details className="result-card"><summary>Text that was analyzed</summary><p className="input-preview">{result.analyzed_text}</p></details>
    <p className="notice">{result.disclaimer}</p>
  </section>;
}

export default function Popup() {
  const [text, setText] = useState(''), [page, setPage] = useState(EMPTY_PAGE);
  const [file, setFile] = useState(null), [kind, setKind] = useState('image');
  const [status, setStatus] = useState('idle'), [error, setError] = useState(''), [result, setResult] = useState(null);
  const [lookup, setLookup] = useState(false);
  const [enabled, setEnabled] = useState(true);
  const lock = useRef(false);
  const busy = !['idle', 'completed', 'failed'].includes(status);
  useEffect(() => {
    // Remove data from retired prototype flows; keep only active user preferences.
    chrome.storage.local.remove(['suriphLastResult', 'suriphLastText', 'suriphLastPage', 'suriphReceipts']);
    chrome.storage.local.get({ suriphEnabled: true, suriphRetrieveSources: false }, saved => { setEnabled(saved.suriphEnabled); setLookup(saved.suriphRetrieveSources); });
  }, []);
  const clearResult = () => { setResult(null); setError(''); setStatus('idle'); };
  async function perform(nextStatus, action) {
    if (lock.current) return;
    lock.current = true; setStatus(nextStatus); setError(''); setResult(null);
    try { await action(); setStatus('completed'); }
    catch (reason) { setError(reason.message || 'The service is unavailable. Try again later.'); setStatus('failed'); }
    finally { lock.current = false; }
  }
  const show = output => setResult(output);
  async function extract(mode) {
    await perform('Reading selected content', async () => {
      const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
      if (!tab?.id) throw new Error('Open a supported page first.');
      const response = await chrome.tabs.sendMessage(tab.id, { type: 'SURIPH_EXTRACT', mode });
      if (!response?.ok || !response.text?.trim()) throw new Error(response?.error || 'No readable text was found. Select text on a supported page, or paste it here.');
      setText(response.text); setPage({ url: tab.url, title: tab.title });
    });
  }
  const options = { retrieveSources: lookup };
  async function runText() { await perform('Analyzing text', async () => {
    if (!text.trim()) throw new Error('Enter or select text before analyzing.');
    await show(await analyzeText({ text, pageUrl: page.url, pageTitle: page.title, ...options }));
  }); }
  async function runMedia() { await perform('Extracting and analyzing media', async () => {
    if (!file) throw new Error('Choose a file first.');
    const output = await analyzeMedia(kind, file, { ...page, ...options }); setText(output.analyzed_text); await show(output);
  }); }
  async function setPageTools(next) {
    setEnabled(next);
    await chrome.storage.local.set({ suriphEnabled: next });
    const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
    if (tab?.id) await chrome.tabs.reload(tab.id);
  }
  return <main className="popup-shell">
    <header className="brand-row"><div><h1>SuriPH</h1><p>Read carefully. Check the context.</p></div><button type="button" className="page-tools-toggle" role="switch" aria-checked={enabled} disabled={busy} onClick={() => setPageTools(!enabled)} title="Turn SuriPH controls on or off and reload this page"><span className="toggle-label">Page tools </span><span className="toggle-track" aria-hidden="true"><span className="toggle-knob" /></span><strong>{enabled ? 'on' : 'off'}</strong></button></header>
    <section className="result-card input-card"><label htmlFor="screen-text">Text to analyze</label>
      <p>Use public, non-sensitive content. Text is processed by the study server; it is not saved by default. Use the complete post caption or article text; brief isolated statements can receive unreliable extreme scores.</p>
      <textarea id="screen-text" rows={6} value={text} disabled={busy} onChange={event => { setText(event.target.value); setPage(EMPTY_PAGE); clearResult(); }} placeholder="Paste English, Filipino or Taglish text…" />
      <div className="button-row"><button className="secondary" disabled={busy} onClick={() => extract('selection')}>Use selected text</button><button className="secondary" disabled={busy} onClick={() => extract('post')}>Use post caption</button></div>
      <fieldset disabled={busy} className="choices"><legend>External lookup</legend>
        <label><input type="checkbox" checked={lookup} onChange={e => { const next = e.target.checked; setLookup(next); chrome.storage.local.set({ suriphRetrieveSources: next }); clearResult(); }} />Search related reading and published fact-check reviews. Send up to 500 characters of the text to Serper and Google Fact Check. This setting also applies to the in-page S button.</label>
      </fieldset>
      <p className="small">Analysis results are not saved by the screening service. External lookup is optional and does not change the classifier prediction. Do not submit private or identifying content.</p>
      <button className="primary" disabled={busy} onClick={runText}>Analyze text</button>
    </section>
    <details className="result-card"><summary>Optional image or video extraction</summary><p>Experimental acquisition: review extracted text. Quality depends on the media and server support; this is not a validated OCR or transcription assessment.</p>
      <label htmlFor="media-kind">Media type</label><select id="media-kind" disabled={busy} value={kind} onChange={e => { setKind(e.target.value); setFile(null); clearResult(); }}><option value="image">Image OCR</option><option value="video">Video and audio</option></select>
      <label htmlFor="media-file">Choose a file (maximum 50 MiB)</label><input key={kind} id="media-file" disabled={busy} type="file" accept={kind === 'image' ? 'image/*' : 'video/*'} onChange={e => { setFile(e.target.files?.[0] || null); clearResult(); }} />
      <button className="secondary" disabled={busy || !file} onClick={runMedia}>Extract and analyze {kind}</button>
    </details>
    <div aria-live="polite" role="status">{busy && <p className="notice">{status}… Please keep this popup open.</p>}</div>
    {error && <p role="alert" className="error">{error}</p>}
    {!result && !busy && !error && <p className="empty-state">Your prediction and seven text measurements will appear here.</p>}
    <Result result={result} />
    <footer><button className="text-button" disabled={busy} onClick={() => { setText(''); setPage(EMPTY_PAGE); setFile(null); clearResult(); }}>Clear this input and result</button><p>Research prototype · Predictions can be wrong.</p></footer>
  </main>;
}
