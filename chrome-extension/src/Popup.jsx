import React, { useEffect, useRef, useState } from 'react';
import { analyzeMedia, analyzeText, lookupRelatedSources } from './api.js';

const EMPTY_PAGE = { url: '', title: '', context: null, postText: '' };
const copy = {
  en: {
    tagline: 'Read carefully. Check the context.', pageTools: 'Page tools', on: 'on', off: 'off', toggleTitle: 'Turn SuriPH page controls on or off and reload Facebook',
    textLabel: 'Text to assess', inputHelp: 'Review the complete public Facebook text before looking for evidence. The assessment is not stored by default.', placeholder: 'Paste English, Filipino or Taglish text…', selected: 'Use selected text', caption: 'Use Facebook post caption', lookup: 'Search evidence providers', lookupHelp: 'Send the selected or extracted text to approved-source search and Google Fact Check. Results do not become a verdict unless a closely matching published fact-check is found.', privacy: 'Do not submit private or identifying content.', analyze: 'Check evidence', mediaTitle: 'Optional image or video extraction', mediaHelp: 'Review the extracted text. Quality depends on the media and server support.', mediaType: 'Media type', image: 'Image OCR', video: 'Video speech and frame text', choose: 'Choose a file (maximum 50 MiB)', extract: 'Extract and check', clear: 'Clear input', empty: 'The evidence assessment will appear here.',
    reading: 'Reading selected Facebook content', analyzing: 'Analyzing text', mediaBusy: 'Extracting and analyzing media', keepOpen: 'Please keep this popup open.', noTab: 'Open Facebook in the active tab first.', noText: 'No readable Facebook post text was found. Select the exact text or paste it here.', enter: 'Enter or select text before analyzing.', noFile: 'Choose a file first.', unavailable: 'The screening service is unavailable. Try again later.',
    assessment: 'EVIDENCE ASSESSMENT', basis: 'Why this result is shown', sourceKind: 'Decision source', noClassifier: 'No trained classifier, model score or probability was used.',
    contextTitle: 'Post context', author: 'Who posted it', postTime: 'When posted', recency: 'How recent', checkedMaterial: 'What was checked', postLinks: 'Links in the selected post', notAvailable: 'Not available', couldNotDetermine: 'Could not determine', openPost: 'Open original post',
    factChecks: 'Published fact-checks', factCheckHelp: 'Only closely matching Google ClaimReview records can supply a published rating.', noFactCheck: 'No closely matching published fact-check was found.', rating: 'Published rating',
    related: 'Related context and credible sources', relatedHelp: 'Approved-publisher articles are related reading. Their presence alone does not prove or disprove the post.', findSources: 'Search evidence providers', findingSources: 'Searching evidence providers…', lookupOff: 'Evidence lookup was not requested.', noRelated: 'No relevant results were returned from approved publishers.', lookupUnavailable: 'The evidence provider is unavailable. No verdict was produced.', lookupFailed: 'The evidence request failed. No verdict was produced.', missingLinks: 'Missing links do not show that a post is true or false.', publisherMissing: 'Publisher not supplied', searchResult: 'Related article',
    analyzed: 'Assessed text', analyzedHelp: 'Exact text sent to the evidence providers. It has not been translated or summarized.',
    reminder: 'SuriPH searches for published fact-checks and related reporting. Related links are context, not proof. If no closely matching published fact-check is available, SuriPH leaves the post unresolved.',
    checkAgain: 'Check again',
  },
  tl: {
    tagline: 'Basahing mabuti. Suriin ang konteksto.', pageTools: 'Mga kontrol sa page', on: 'on', off: 'off', toggleTitle: 'I-on o i-off ang mga kontrol ng SuriPH at i-reload ang Facebook',
    textLabel: 'Tekstong susuriin', inputHelp: 'Basahin muna ang buong pampublikong Facebook text bago maghanap ng ebidensya. Hindi sine-save ang assessment bilang default.', placeholder: 'I-paste ang English, Filipino, o Taglish na teksto…', selected: 'Gamitin ang piniling teksto', caption: 'Gamitin ang caption ng Facebook post', lookup: 'Maghanap sa evidence providers', lookupHelp: 'Ipadala ang teksto sa approved-source search at Google Fact Check. Hindi ito magiging verdict maliban kung may malapit na published fact-check.', privacy: 'Huwag magsumite ng pribado o makakakilalang impormasyon.', analyze: 'Suriin ang ebidensya', mediaTitle: 'Opsyonal na pagkuha mula sa image o video', mediaHelp: 'Suriin ang nakuhang teksto. Nakadepende ang kalidad sa media at server.', mediaType: 'Uri ng media', image: 'Teksto sa image (OCR)', video: 'Salita at teksto sa frame ng video', choose: 'Pumili ng file (hanggang 50 MiB)', extract: 'Kunin at suriin', clear: 'Burahin ang input', empty: 'Dito lalabas ang evidence assessment.',
    reading: 'Binabasa ang piniling Facebook content', analyzing: 'Sinusuri ang teksto', mediaBusy: 'Kinukuha at sinusuri ang media', keepOpen: 'Panatilihing bukas ang popup.', noTab: 'Buksan muna ang Facebook sa aktibong tab.', noText: 'Walang nakitang mababasang Facebook post text. Piliin ang eksaktong teksto o i-paste ito rito.', enter: 'Maglagay o pumili muna ng teksto.', noFile: 'Pumili muna ng file.', unavailable: 'Hindi magamit ang screening service. Subukan muli mamaya.',
    assessment: 'EVIDENCE ASSESSMENT', basis: 'Bakit ito ang ipinapakita', sourceKind: 'Pinagmulan ng assessment', noClassifier: 'Walang trained classifier, model score, o probability na ginamit.',
    contextTitle: 'Konteksto ng post', author: 'Sino ang nag-post', postTime: 'Kailan na-post', recency: 'Gaano kabago', checkedMaterial: 'Ano ang sinuri', postLinks: 'Mga link sa piniling post', notAvailable: 'Hindi available', couldNotDetermine: 'Hindi matukoy', openPost: 'Buksan ang orihinal na post',
    factChecks: 'Mga published fact-check', factCheckHelp: 'Tanging malapit na Google ClaimReview record ang maaaring magbigay ng published rating.', noFactCheck: 'Walang nakitang malapit na published fact-check.', rating: 'Published rating',
    related: 'Kaugnay na konteksto at mapagkakatiwalaang source', relatedHelp: 'Kaugnay na babasahin ang mga artikulo mula sa aprubadong publisher. Hindi sapat ang presensya nila para patunayan o pabulaanan ang post.', findSources: 'Maghanap sa evidence providers', findingSources: 'Naghahanap sa evidence providers…', lookupOff: 'Hindi hiniling ang evidence lookup.', noRelated: 'Walang relevant result mula sa mga aprubadong publisher.', lookupUnavailable: 'Hindi magamit ang evidence provider. Walang verdict na ginawa.', lookupFailed: 'Hindi nakumpleto ang evidence request. Walang verdict na ginawa.', missingLinks: 'Hindi pinatutunayan ng kawalan ng link na totoo o mali ang post.', publisherMissing: 'Walang ibinigay na publisher', searchResult: 'Kaugnay na artikulo',
    analyzed: 'Sinuring teksto', analyzedHelp: 'Eksaktong tekstong ipinadala sa evidence providers. Hindi ito isinalin o ginawan ng summary.',
    reminder: 'Naghahanap ang SuriPH ng published fact-checks at kaugnay na ulat. Konteksto lamang ang related links, hindi patunay. Kung walang malapit na published fact-check, mananatiling unresolved ang post.',
    checkAgain: 'Suriin muli',
  },
};

const safeUrl = value => { try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) ? url.href : null; } catch { return null; } };
const localizedError = (message, language, t) => {
  if (language === 'en' || !message) return message || t.unavailable;
  if (/timed out|too long/i.test(message)) return 'Nag-timeout ang request. Subukan ang mas maikling input.';
  if (/empty|no usable|no readable|enter or select/i.test(message)) return t.enter;
  if (/media|image|video|ocr|transcri/i.test(message)) return 'Hindi nakuha o naproseso ang media. Suriin ang file at subukan muli.';
  if (/unavailable|connection|backend|service/i.test(message)) return t.unavailable;
  return 'Hindi nakumpleto ang request. Subukan muli.';
};

export function LanguageSwitch({ language, onChange }) {
  return <div className="language-switch" role="group" aria-label="Interface language"><button type="button" aria-pressed={language === 'en'} onClick={() => onChange('en')}>English</button><button type="button" aria-pressed={language === 'tl'} onClick={() => onChange('tl')}>Tagalog</button></div>;
}

function SourceStatus({ result, sourceState, t, onFindSources }) {
  const status = sourceState === 'failed' ? 'failed' : result.retrieval_status;
  if (sourceState === 'loading') return <p className="notice" role="status">{t.findingSources}</p>;
  if (result.related_sources?.length) return result.related_sources.filter(source => safeUrl(source.url)).map(source => <article className="source" key={source.url}><a href={safeUrl(source.url)} target="_blank" rel="noopener noreferrer">{source.title}</a><p>{source.source || t.publisherMissing}{source.date ? ` · ${source.date}` : ''} · {t.searchResult}</p>{source.snippet && <p>{source.snippet}</p>}</article>);
  const message = status === 'not_requested' ? t.lookupOff : status === 'no_results' ? t.noRelated : status === 'failed' ? t.lookupFailed : t.lookupUnavailable;
  return <><p className="notice">{message} {t.missingLinks}</p>{status === 'not_requested' && <button type="button" className="secondary full-width" onClick={onFindSources}>{t.findSources}</button>}</>;
}

function FactCheckStatus({ result, t }) {
  const matches = (result.fact_check_matches || []).filter(item => safeUrl(item.url));
  if (!matches.length) return <p className="notice">{result.fact_check_status === 'not_requested' ? t.lookupOff : t.noFactCheck}</p>;
  return matches.map(item => <article className="source" key={item.url}><a href={safeUrl(item.url)} target="_blank" rel="noopener noreferrer">{item.title || item.claim}</a><p>{item.publisher || t.publisherMissing} · {t.rating}: <strong>{item.rating}</strong></p>{item.claim && <p>{item.claim}</p>}</article>);
}

export function Result({ result, language = 'en', onLanguageChange = () => {}, sourceState = 'idle', onFindSources = () => {}, onCheckAgain = () => {} }) {
  if (!result) return null;
  const t = copy[language]; const context = result.context_explanation || {};
  const postLinks = (context.relevant_links || []).filter(safeUrl); const originalPost = safeUrl(context.original_post_url);
  return <section className="result-stack" aria-label="Evidence result"><LanguageSwitch language={language} onChange={onLanguageChange} />
    <article className={`result-card prediction-card ${['unresolved', 'providers_unavailable'].includes(result.assessment_status) ? 'warning' : 'clear'}`} data-result-part="1-assessment"><p className="eyebrow">{t.assessment}</p><h2>{result.assessment_label}</h2></article>
    <article className="result-card score-card" data-result-part="2-basis"><h3>{t.basis}</h3><p>{result.assessment_basis}</p><p className="small">{t.sourceKind}: {result.decision_source}</p><p className="small">{t.noClassifier}</p></article>
    <article className="result-card context-card" data-result-part="3-post-context"><h3>{t.contextTitle}</h3><dl className="context-list"><div><dt>{t.author}</dt><dd>{context.author || t.notAvailable}</dd></div><div><dt>{t.postTime}</dt><dd>{context.timing || t.notAvailable}</dd></div><div><dt>{t.recency}</dt><dd>{context.recency || t.couldNotDetermine}</dd></div><div><dt>{t.checkedMaterial}</dt><dd>{context.checked_material || t.notAvailable}</dd></div></dl>{originalPost && <p><a href={originalPost} target="_blank" rel="noopener noreferrer">{t.openPost}</a></p>}{postLinks.length > 0 && <details><summary>{t.postLinks}</summary><ul>{postLinks.map(url => <li key={url}><a href={url} target="_blank" rel="noopener noreferrer">{url}</a></li>)}</ul></details>}</article>
    <section className="result-card" data-result-part="4-fact-checks"><h3>{t.factChecks}</h3><p>{t.factCheckHelp}</p><FactCheckStatus result={result} t={t} /></section>
    <section className="result-card" data-result-part="5-related-sources"><h3>{t.related}</h3><p>{t.relatedHelp}</p><SourceStatus result={result} sourceState={sourceState} t={t} onFindSources={onFindSources} /></section>
    <details className="result-card analyzed-card" data-result-part="6-analyzed-text"><summary>{t.analyzed}</summary><p className="small">{t.analyzedHelp}</p><p className="input-preview full-text">{result.analyzed_text}</p></details>
    <p className="friendly-reminder" data-result-part="7-reminder">{t.reminder}</p>
    <button type="button" className="primary result-check-again" data-result-part="8-check-again" onClick={onCheckAgain}>{t.checkAgain}</button>
  </section>;
}

export default function Popup() {
  const [text, setText] = useState(''), [page, setPage] = useState(EMPTY_PAGE), [file, setFile] = useState(null), [kind, setKind] = useState('image');
  const [status, setStatus] = useState('idle'), [error, setError] = useState(''), [result, setResult] = useState(null), [sourceState, setSourceState] = useState('idle');
  const [lookup, setLookup] = useState(true), [enabled, setEnabled] = useState(true), [language, setLanguage] = useState('en');
  const lock = useRef(false), sourceLock = useRef(false), textRef = useRef(null); const busy = !['idle', 'completed', 'failed'].includes(status); const t = copy[language];
  useEffect(() => { chrome.storage.local.remove(['suriphLastResult', 'suriphLastText', 'suriphLastPage', 'suriphReceipts']); chrome.storage.local.get({ suriphEnabled: true, suriphRetrieveSources: true, suriphLanguage: 'en' }, saved => { setEnabled(saved.suriphEnabled); setLookup(saved.suriphRetrieveSources); setLanguage(saved.suriphLanguage === 'tl' ? 'tl' : 'en'); }); }, []);
  const changeLanguage = next => { setLanguage(next); chrome.storage.local.set({ suriphLanguage: next }); };
  const clearResult = () => { setResult(null); setError(''); setStatus('idle'); setSourceState('idle'); sourceLock.current = false; };
  const checkAgain = () => { clearResult(); requestAnimationFrame(() => textRef.current?.focus()); };
  async function perform(nextStatus, action) { if (lock.current) return; lock.current = true; setStatus(nextStatus); setError(''); setResult(null); setSourceState('idle'); try { await action(); setStatus('completed'); } catch (reason) { setError(localizedError(reason.message, language, t)); setStatus('failed'); } finally { lock.current = false; } }
  async function extract(mode) { await perform(t.reading, async () => { const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true }); if (!tab?.id || !/^https:\/\/([^/]+\.)?facebook\.com\//i.test(tab.url || '')) throw new Error(t.noTab); const response = await chrome.tabs.sendMessage(tab.id, { type: 'SURIPH_EXTRACT', mode }); if (!response?.ok || !response.text?.trim()) throw new Error(response?.error || t.noText); setText(response.text); setPage({ url: tab.url, title: tab.title, context: response.context || null, postText: response.mode === 'post' ? response.text : '' }); }); }
  async function runText() { await perform(t.analyzing, async () => { if (!text.trim()) throw new Error(t.enter); setResult(await analyzeText({ text, pageUrl: page.url, pageTitle: page.title, context: page.context, retrieveSources: lookup })); }); }
  async function runMedia() { await perform(t.mediaBusy, async () => { if (!file) throw new Error(t.noFile); const output = await analyzeMedia(kind, file, { ...page, retrieveSources: lookup }); setText(output.analyzed_text); setResult(output); }); }
  async function findSources() { if (!result || sourceLock.current) return; sourceLock.current = true; setSourceState('loading'); try { const sources = await lookupRelatedSources({ text: result.analyzed_text, pageUrl: result.page_url }); setResult(current => ({ ...current, ...sources })); setSourceState('completed'); setLookup(true); chrome.storage.local.set({ suriphRetrieveSources: true }); } catch { setSourceState('failed'); } finally { sourceLock.current = false; } }
  async function setPageTools(next) { setEnabled(next); await chrome.storage.local.set({ suriphEnabled: next }); const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true }); if (tab?.id && /^https:\/\/([^/]+\.)?facebook\.com\//i.test(tab.url || '')) await chrome.tabs.reload(tab.id); }
  return <main className="popup-shell"><header className="brand-row"><div><h1>SuriPH</h1><p>{t.tagline}</p></div><button type="button" className="page-tools-toggle" role="switch" aria-checked={enabled} disabled={busy} onClick={() => setPageTools(!enabled)} title={t.toggleTitle}><span className="toggle-label">{t.pageTools}</span><span className="toggle-track" aria-hidden="true"><span className="toggle-knob" /></span><strong>{enabled ? t.on : t.off}</strong></button></header>
    {!result && <LanguageSwitch language={language} onChange={changeLanguage} />}
    {!result && <><section className="result-card input-card"><label htmlFor="screen-text">{t.textLabel}</label><p>{t.inputHelp}</p><textarea ref={textRef} id="screen-text" rows={6} value={text} disabled={busy} onChange={event => { setText(event.target.value); setPage(EMPTY_PAGE); clearResult(); }} placeholder={t.placeholder} /><div className="button-row"><button className="secondary" disabled={busy} onClick={() => extract('selection')}>{t.selected}</button><button className="secondary" disabled={busy} onClick={() => extract('post')}>{t.caption}</button></div><fieldset disabled={busy} className="choices"><legend>{t.lookup}</legend><label><input type="checkbox" checked={lookup} onChange={event => { const next = event.target.checked; setLookup(next); chrome.storage.local.set({ suriphRetrieveSources: next }); clearResult(); }} />{t.lookupHelp}</label></fieldset><p className="small">{t.privacy}</p><button className="primary" disabled={busy} onClick={runText}>{t.analyze}</button></section>
    <details className="result-card"><summary>{t.mediaTitle}</summary><p>{t.mediaHelp}</p><label htmlFor="media-kind">{t.mediaType}</label><select id="media-kind" disabled={busy} value={kind} onChange={event => { setKind(event.target.value); setFile(null); clearResult(); }}><option value="image">{t.image}</option><option value="video">{t.video}</option></select><label htmlFor="media-file">{t.choose}</label><input key={kind} id="media-file" disabled={busy} type="file" accept={kind === 'image' ? 'image/*' : 'video/*'} onChange={event => { setFile(event.target.files?.[0] || null); clearResult(); }} /><button className="secondary full-width" disabled={busy || !file} onClick={runMedia}>{t.extract} {kind === 'image' ? t.image : t.video}</button></details></>}
    <div aria-live="polite" role="status">{busy && <p className="notice">{status}… {t.keepOpen}</p>}</div>{error && <p role="alert" className="error">{error}</p>}{!result && !busy && !error && <p className="empty-state">{t.empty}</p>}
    <Result result={result} language={language} onLanguageChange={changeLanguage} sourceState={sourceState} onFindSources={findSources} onCheckAgain={checkAgain} />
    {!result && <footer><button className="text-button" disabled={busy} onClick={() => { setText(''); setPage(EMPTY_PAGE); setFile(null); clearResult(); }}>{t.clear}</button></footer>}
  </main>;
}
