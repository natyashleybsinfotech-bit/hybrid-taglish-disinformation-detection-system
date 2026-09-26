import React, { useEffect, useState } from 'react';
import { analyzeMedia, analyzeText } from './api.js';

const EMPTY_PAGE = { url: '', title: '' };

function Result({ result }) {
  if (!result) return null;
  const context = result.context_explanation;
  return (
    <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-3 text-slate-900 shadow-sm">
      <strong className="block w-full rounded-lg bg-emerald-500 px-3 py-3 text-center text-sm text-emerald-950">
        {result.public_label}
      </strong>
      <p className="text-xs font-bold text-slate-700">Confidence: {(result.temporary_score * 100).toFixed(1)}%</p>
      {result.decision_source === 'google_fact_check' && result.decision_basis && (
        <p className="rounded-lg border border-violet-200 bg-violet-50 p-2 text-[11px] font-medium text-violet-900">
          Google fact-check evidence influenced this result: {result.decision_basis}
        </p>
      )}

      <div className="rounded-lg border border-sky-200 bg-sky-50 p-2">
        <p className="text-[10px] font-bold uppercase tracking-wide text-slate-600">Related coverage from credible sources</p>
        {!result.related_sources?.length && <p className="mt-1 text-[11px] text-slate-600">{result.retrieval_status === 'unavailable' ? 'Credible-source lookup is temporarily unavailable. Try again.' : 'No matching credible article was found for this claim.'}</p>}
        {result.related_sources?.map((source) => (
          <a key={source.url} href={source.url} target="_blank" rel="noreferrer" className="block truncate text-[11px] text-sky-400 hover:underline">
            {source.title || source.url}
          </a>
        ))}
      </div>

      <div className="rounded-lg border border-violet-200 bg-violet-50 p-2 text-xs text-slate-700">
        <p className="font-bold text-violet-800">Published fact-checks from Google Fact Check Tools</p>
        {!result.fact_check_matches?.length && <p className="mt-1 text-[11px]">{result.fact_check_status === 'unavailable_not_configured' ? 'Google Fact Check is ready, but its API key has not been configured yet.' : result.fact_check_status === 'unavailable' ? 'Google Fact Check is temporarily unavailable.' : 'No previously fact-checked claim matched this post.'}</p>}
        {result.fact_check_matches?.map((match) => <div key={match.url} className="mt-2 border-t border-violet-200 pt-2">
          <p className="font-semibold">{match.publisher}: {match.rating}</p>
          <a href={match.url} target="_blank" rel="noreferrer" className="block truncate text-[11px] text-sky-700 hover:underline">{match.title || match.claim || 'Open fact-check article'}</a>
        </div>)}
      </div>

      {context && <div className="space-y-2 rounded-xl border border-teal-200 bg-teal-50 p-3 text-xs text-teal-950">
        <h2 className="text-sm font-bold text-teal-700">Context overview</h2>
        <div>
          <p className="font-semibold">What the post is about</p>
          <p className="mt-1 leading-relaxed">{context.overview || 'There was not enough readable content to produce a clear overview.'}</p>
        </div>
        {!!context.separate_statements?.length && <details className="rounded-lg border border-teal-200 bg-white p-2">
          <summary className="cursor-pointer font-semibold text-teal-700">View {context.separate_statements.length} separate statements</summary>
          <div className="mt-2 space-y-1.5">
          {context.separate_statements.map((claim) => <div key={`${claim.number}-${claim.statement}`} className="rounded-lg border border-teal-100 bg-white p-2 text-slate-700">
            <p>{claim.number}. {claim.statement}</p>
          </div>)}
          </div>
        </details>}
        <div className="grid grid-cols-1 gap-1 rounded-lg bg-white p-2 text-slate-700">
          <p><strong>Source:</strong> {context.author}</p>
          <p><strong>Posted:</strong> {context.timing}</p>
          <p><strong>Recency:</strong> {context.freshness}</p>
        </div>
        {context.recency_explanation && <p className="leading-relaxed"><strong>Why timing matters:</strong> {context.recency_explanation}</p>}
        {context.assessment_scope && <p className="leading-relaxed"><strong>How the statements were checked:</strong> {context.assessment_scope}</p>}
        {context.checked_material && <p className="leading-relaxed"><strong>Content used:</strong> {context.checked_material}</p>}
        {context.related_coverage && <p className="leading-relaxed"><strong>Related coverage:</strong> {context.related_coverage}</p>}
      </div>}

      <details className="rounded-lg border border-slate-200 bg-slate-50 p-2">
        <summary className="cursor-pointer text-xs font-semibold text-slate-700">View the content checked by SuriPH</summary>
        <p className="mt-2 max-h-28 overflow-auto text-[11px] leading-relaxed text-slate-600">{result.analyzed_text}</p>
      </details>
      <div className="rounded-lg border border-amber-300 border-l-4 bg-amber-50 p-2 text-[11px] font-semibold leading-relaxed text-amber-900">{result.disclaimer}</div>
    </section>
  );
}

export default function Popup() {
  const [text, setText] = useState('');
  const [page, setPage] = useState(EMPTY_PAGE);
  const [file, setFile] = useState(null);
  const [mediaKind, setMediaKind] = useState('image');
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [enabled, setEnabled] = useState(true);

  useEffect(() => { chrome.storage.local.get({ suriphLastResult: null, suriphLastText: '', suriphLastPage: EMPTY_PAGE }, (saved) => { if (saved.suriphLastResult) { setResult(saved.suriphLastResult); setText(saved.suriphLastText || saved.suriphLastResult.analyzed_text || ''); setPage(saved.suriphLastPage || EMPTY_PAGE); setStatus('completed'); } }); }, []);

  useEffect(() => { chrome.storage.local.get({ suriphEnabled: true }, (settings) => setEnabled(settings.suriphEnabled !== false)); }, []);

  const toggleExtension = async () => {
    const next = !enabled; setEnabled(next);
    await chrome.storage.local.set({ suriphEnabled: next });
    const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
    if (tab?.id) { try { await chrome.tabs.sendMessage(tab.id, { type: 'SURIPH_SET_ENABLED', enabled: next }); } catch (_) { /* unsupported page */ } try { await chrome.tabs.reload(tab.id); } catch (_) { /* tab closed */ } }
  };

  const fail = (reason) => {
    setStatus('failed');
    setError(reason?.message || String(reason));
  };

  const extract = async (mode) => {
    setStatus('extracting'); setError(''); setResult(null);
    try {
      const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
      if (!tab?.id) throw new Error('No active page is available.');
      const response = await chrome.tabs.sendMessage(tab.id, { type: 'SURIPH_EXTRACT', mode });
      if (!response?.ok) throw new Error(response?.error || 'This page is not supported by the extension.');
      if (!response.text) throw new Error(mode === 'selection' ? 'Select text on the page first.' : 'No supported post text was found.');
      setText(response.text);
      setPage({ url: response.pageUrl, title: response.pageTitle });
      setStatus('idle');
    } catch (reason) { fail(reason); }
  };

  const runText = async () => {
    if (!text.trim()) return fail(new Error('Enter or extract text before screening.'));
    setStatus('analyzing'); setError(''); setResult(null);
    try {
      const output = await analyzeText({ text, pageUrl: page.url, pageTitle: page.title }); setResult(output); await chrome.storage.local.set({ suriphLastResult: output, suriphLastText: text, suriphLastPage: page });
      setStatus('completed');
    } catch (reason) { fail(reason); }
  };

  const runMedia = async () => {
    if (!file) return fail(new Error(`Choose an ${mediaKind} file first.`));
    setStatus('processing_media'); setError(''); setResult(null);
    try {
      const response = await analyzeMedia(mediaKind, file, page);
      setResult(response); setText(response.analyzed_text); await chrome.storage.local.set({ suriphLastResult: response, suriphLastText: response.analyzed_text, suriphLastPage: page }); setStatus('completed');
    } catch (reason) { fail(reason); }
  };

  return (
    <main className="popup-shell max-h-[620px] w-[390px] overflow-auto bg-white p-4 font-sans text-slate-900">
      <header className="mb-3 flex items-start justify-between gap-3">
        <div><h1 className="text-base font-bold text-teal-700">SuriPH</h1>
        <p className="text-[10px] text-slate-500">Check posts, images, and videos with context</p>
        </div>
        <div className="flex items-center gap-1.5"><button onClick={toggleExtension} className={`flex items-center gap-1.5 rounded-full border px-2 py-1 text-[10px] ${enabled ? 'border-emerald-500/60 text-emerald-300' : 'border-slate-600 text-slate-400'}`} aria-pressed={enabled}><span className={`h-2 w-2 rounded-full ${enabled ? 'bg-emerald-400' : 'bg-slate-500'}`} />{enabled ? 'On' : 'Off'}</button><button onClick={() => window.close()} aria-label="Close SuriPH popup" className="rounded-full border border-slate-700 px-2 py-0.5 text-sm leading-none text-slate-400 hover:border-slate-500 hover:text-white">×</button></div>
      </header>
      <section className="space-y-2">
        <textarea value={text} onChange={(event) => setText(event.target.value)} maxLength={20000} rows={6} placeholder="Paste text, or extract it from the active page…" className="w-full resize-y rounded border border-slate-700 bg-slate-900 p-2 text-xs outline-none focus:border-emerald-500" />
        <div className="grid grid-cols-2 gap-2">
          <button onClick={() => extract('selection')} className="rounded border border-slate-700 p-2 text-xs hover:bg-slate-800">Use selected text</button>
          <button onClick={() => extract('post')} className="rounded border border-slate-700 p-2 text-xs hover:bg-slate-800">Extract supported post</button>
        </div>
        <button onClick={runText} disabled={['extracting', 'analyzing', 'processing_media'].includes(status)} className="w-full rounded bg-emerald-600 p-2 text-xs font-semibold hover:bg-emerald-500 disabled:opacity-50">Check text</button>
      </section>
      <section className="my-3 space-y-2 border-y border-slate-200 py-3">
        <div className="grid grid-cols-2 gap-2">
          {['image', 'video'].map((kind) => <button key={kind} onClick={() => { setMediaKind(kind); setFile(null); }} className={`rounded p-1.5 text-xs ${mediaKind === kind ? 'bg-sky-700' : 'bg-slate-800'}`}>{kind === 'image' ? 'Image OCR' : 'Video + audio'}</button>)}
        </div>
        <input type="file" accept={mediaKind === 'image' ? 'image/*' : 'video/*'} onChange={(event) => setFile(event.target.files?.[0] || null)} className="block w-full text-[11px] text-slate-400 file:mr-2 file:rounded file:border-0 file:bg-slate-700 file:px-2 file:py-1 file:text-white" />
        <button onClick={runMedia} disabled={!file || status === 'processing_media'} className="w-full rounded bg-sky-700 p-2 text-xs font-semibold hover:bg-sky-600 disabled:opacity-50">Check {mediaKind}</button>
      </section>
      {!['idle', 'completed', 'failed'].includes(status) && <p className="mb-3 text-xs text-sky-300">Status: {(status === 'analyzing' ? 'screening' : status === 'processing_media' ? 'processing media' : status.replace('_', ' '))}...</p>}
      {error && <p role="alert" className="mb-3 rounded border border-red-800 bg-red-950/50 p-2 text-xs text-red-300">{error}</p>}
      <Result result={result} />
    </main>
  );
}
