import React, { useEffect, useRef, useState } from 'react';
import { analyzeMedia, analyzeText, submitCandidate } from './api.js';

const EMPTY_PAGE = { url: '', title: '', context: null, postText: '' };
const copy = {
  en: {
    tagline: 'Read carefully. Check the context.', pageTools: 'Page tools', on: 'on', off: 'off', toggleTitle: 'Turn SuriPH page controls on or off and reload Facebook',
    textLabel: 'Text to check', inputHelp: 'Review the complete public Facebook text before checking it. SuriPH does not save it by default.', placeholder: 'Paste English, Filipino or Taglish text…', selected: 'Use selected text', caption: 'Use Facebook post caption', lookup: 'Check reliable sources', lookupHelp: 'Look for related news reports and fact-checks that can help assess the post.', privacy: 'Do not submit private or identifying content.', analyze: 'Check text', mediaTitle: 'Check an image or video', mediaHelp: 'Review the text found in the media before relying on the result.', mediaType: 'Media type', image: 'Text in an image', video: 'Speech and text in a video', choose: 'Choose a file (maximum 50 MiB)', extract: 'Extract and check', clear: 'Clear input', empty: 'Your result and related sources will appear here.',
    reading: 'Reading selected Facebook content', analyzing: 'Analyzing text', mediaBusy: 'Extracting and analyzing media', keepOpen: 'Please keep this popup open.', noTab: 'Open Facebook in the active tab first.', noText: 'No readable Facebook post text was found. Select the exact text or paste it here.', enter: 'Enter or select text before analyzing.', noFile: 'Choose a file first.', unavailable: 'The screening service is unavailable. Try again later.',
    prediction: 'SuriPH RESULT', why: 'Why this result', officialSupport: 'A reliable official source supports the main claim in this post.', multipleSupport: 'Several reliable sources report the same main claim.', factCheckSupport: 'A published fact-check supports the main claim in this post.', factCheckWarning: 'A published fact-check says the main claim is false or misleading.', textClear: 'The text check did not find enough warning signs to flag this post.', textWarning: 'The text check found warning signs that may indicate misleading information.',
    contextTitle: 'About this post', author: 'Posted by', postTime: 'Post date', recency: 'How recent', checkedMaterial: 'Content checked', postLinks: 'Links included in the post', notAvailable: 'Not available', couldNotDetermine: 'Could not determine', openPost: 'Open original post',
    related: 'Related reliable sources', relatedHelp: 'Open these links to compare the post with reporting from reliable sources.', findSources: 'Find related sources', findingSources: 'Finding related sources…', lookupOff: 'Source search was not requested.', noRelated: 'No closely related reliable source was found.', lookupUnavailable: 'Reliable-source search is temporarily unavailable.', lookupFailed: 'The source search could not be completed.', missingLinks: 'This alone does not mean the post is misleading.', publisherMissing: 'Source not listed', factCheckRating: 'Fact-check rating',
    analyzed: 'Text checked', analyzedHelp: 'This is the exact text SuriPH checked.',
    reminder: 'SuriPH can make mistakes. Read the full post, check its date and source, and compare it with reliable references before sharing or acting on it.',
    checkAgain: 'Check again', nextHelp: 'Optionally submit this exact text to the private candidate-review queue for human review.', consent: 'I consent to storing this analyzed text and page metadata for human review. It will not enter a dataset automatically.', submit: 'Submit for human review', submitting: 'Submitting…', submitted: 'Submitted for human review.', candidateError: 'The candidate could not be submitted.',
  },
  tl: {
    tagline: 'Basahing mabuti. Suriin ang konteksto.', pageTools: 'Mga kontrol sa page', on: 'on', off: 'off', toggleTitle: 'I-on o i-off ang mga kontrol ng SuriPH at i-reload ang Facebook',
    textLabel: 'Tekstong susuriin', inputHelp: 'Basahin muna ang buong pampublikong Facebook text. Hindi ito sine-save ng SuriPH bilang default.', placeholder: 'I-paste ang English, Filipino, o Taglish na teksto…', selected: 'Gamitin ang piniling teksto', caption: 'Gamitin ang caption ng Facebook post', lookup: 'Suriin ang mapagkakatiwalaang sources', lookupHelp: 'Maghanap ng kaugnay na balita at fact-checks na makatutulong sa pagsusuri ng post.', privacy: 'Huwag magsumite ng pribado o makakakilalang impormasyon.', analyze: 'Suriin ang teksto', mediaTitle: 'Suriin ang image o video', mediaHelp: 'Basahin ang tekstong nakuha mula sa media bago umasa sa resulta.', mediaType: 'Uri ng media', image: 'Teksto sa image', video: 'Salita at teksto sa video', choose: 'Pumili ng file (hanggang 50 MiB)', extract: 'Kunin at suriin', clear: 'Burahin ang input', empty: 'Dito lalabas ang resulta at mga kaugnay na sources.',
    reading: 'Binabasa ang piniling Facebook content', analyzing: 'Sinusuri ang teksto', mediaBusy: 'Kinukuha at sinusuri ang media', keepOpen: 'Panatilihing bukas ang popup.', noTab: 'Buksan muna ang Facebook sa aktibong tab.', noText: 'Walang nakitang mababasang Facebook post text. Piliin ang eksaktong teksto o i-paste ito rito.', enter: 'Maglagay o pumili muna ng teksto.', noFile: 'Pumili muna ng file.', unavailable: 'Hindi magamit ang screening service. Subukan muli mamaya.',
    prediction: 'RESULTA NG SURIPH', why: 'Bakit ito ang resulta', officialSupport: 'May mapagkakatiwalaang opisyal na source na sumusuporta sa pangunahing pahayag ng post.', multipleSupport: 'May ilang mapagkakatiwalaang source na nag-uulat ng parehong pangunahing pahayag.', factCheckSupport: 'May published fact-check na sumusuporta sa pangunahing pahayag ng post.', factCheckWarning: 'Ayon sa isang published fact-check, mali o misleading ang pangunahing pahayag ng post.', textClear: 'Walang sapat na warning signs na nakita sa pagsusuri ng teksto.', textWarning: 'May nakitang warning signs sa teksto na maaaring nagpapahiwatig ng misleading na impormasyon.',
    contextTitle: 'Tungkol sa post', author: 'Nag-post', postTime: 'Petsa ng post', recency: 'Gaano kabago', checkedMaterial: 'Sinuring content', postLinks: 'Mga link na kasama sa post', notAvailable: 'Hindi available', couldNotDetermine: 'Hindi matukoy', openPost: 'Buksan ang orihinal na post',
    related: 'Kaugnay na mapagkakatiwalaang sources', relatedHelp: 'Buksan ang mga link na ito para maikumpara ang post sa ulat ng mapagkakatiwalaang sources.', findSources: 'Maghanap ng kaugnay na sources', findingSources: 'Naghahanap ng kaugnay na sources…', lookupOff: 'Hindi hiniling ang paghahanap ng sources.', noRelated: 'Walang nakitang malapit na kaugnay na mapagkakatiwalaang source.', lookupUnavailable: 'Pansamantalang hindi magamit ang paghahanap ng sources.', lookupFailed: 'Hindi nakumpleto ang paghahanap ng sources.', missingLinks: 'Hindi nito awtomatikong ibig sabihin na misleading ang post.', publisherMissing: 'Hindi nakalagay ang source', factCheckRating: 'Rating ng fact-check',
    analyzed: 'Tekstong sinuri', analyzedHelp: 'Ito ang eksaktong tekstong sinuri ng SuriPH.',
    reminder: 'Maaaring magkamali ang SuriPH. Basahin ang buong post, tingnan ang petsa at pinagmulan, at ikumpara ito sa mapagkakatiwalaang sanggunian bago ibahagi o aksyunan.',
    checkAgain: 'Suriin muli', nextHelp: 'Opsyonal na isumite ang eksaktong teksto sa pribadong candidate-review queue para sa human review.', consent: 'Pumapayag akong i-store ang sinuring teksto at page metadata para sa human review. Hindi ito awtomatikong isasama sa dataset.', submit: 'Isumite para sa human review', submitting: 'Isinusumite…', submitted: 'Naisumite para sa human review.', candidateError: 'Hindi naisumite ang candidate.',
  },
};

const safeUrl = value => { try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) ? url.href : null; } catch { return null; } };
const displayLabel = result => result?.internal_label === 'Misleading' ? 'Potentially Misleading' : 'No Misleading Information Detected';
const friendlyReason = (result, t) => {
  if (result.decision_source === 'official_primary_source') return t.officialSupport;
  if (result.decision_source === 'corroborated_sources') return t.multipleSupport;
  if (result.decision_source === 'published_fact_check') return result.internal_label === 'Misleading' ? t.factCheckWarning : t.factCheckSupport;
  return result.internal_label === 'Misleading' ? t.textWarning : t.textClear;
};
const friendlyCheckedMaterial = (value, language) => {
  const key = String(value || '').toLowerCase();
  if (key.includes('video audio transcript') || key.includes('video-frame ocr')) return language === 'tl' ? 'Caption, salita, at tekstong lumabas sa video' : 'Caption, spoken audio, and text shown in the video';
  if (key.includes('image ocr')) return language === 'tl' ? 'Caption at tekstong nakita sa image' : 'Caption and text found in the image';
  if (key.includes('caption')) return language === 'tl' ? 'Caption ng post' : 'Post caption';
  if (key.includes('selected')) return language === 'tl' ? 'Piniling teksto' : 'Selected text';
  return value;
};
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
  const factChecks = (result.fact_check_matches || []).filter(source => safeUrl(source.url));
  const sources = (result.related_sources || []).filter(source => safeUrl(source.url));
  if (factChecks.length || sources.length) return <>{factChecks.map(source => <article className="source" key={source.url}><a href={safeUrl(source.url)} target="_blank" rel="noopener noreferrer">{source.title || source.claim}</a><p>{source.publisher || t.publisherMissing} · {t.factCheckRating}: <strong>{source.rating}</strong></p></article>)}{sources.map(source => <article className="source" key={source.url}><a href={safeUrl(source.url)} target="_blank" rel="noopener noreferrer">{source.title}</a><p>{source.source || t.publisherMissing}{source.date ? ` · ${source.date}` : ''}</p>{source.snippet && <p>{source.snippet}</p>}</article>)}</>;
  const message = status === 'not_requested' ? t.lookupOff : status === 'no_results' ? t.noRelated : status === 'failed' ? t.lookupFailed : t.lookupUnavailable;
  return <><p className="notice">{message} {t.missingLinks}</p>{status === 'not_requested' && <button type="button" className="secondary full-width" onClick={onFindSources}>{t.findSources}</button>}</>;
}

export function Result({ result, language = 'en', onLanguageChange = () => {}, sourceState = 'idle', onFindSources = () => {}, onCheckAgain = () => {} }) {
  if (!result) return null;
  const t = copy[language]; const context = result.context_explanation || {};
  const postLinks = (context.relevant_links || []).filter(safeUrl); const originalPost = safeUrl(context.original_post_url);
  return <section className="result-stack" aria-label="Analysis result"><LanguageSwitch language={language} onChange={onLanguageChange} />
    <article className={`result-card prediction-card ${result.internal_label === 'Misleading' ? 'warning' : 'clear'}`} data-result-part="1-prediction"><p className="eyebrow">{t.prediction}</p><h2>{displayLabel(result)}</h2></article>
    <article className="result-card score-card" data-result-part="2-explanation"><h3>{t.why}</h3><p>{friendlyReason(result, t)}</p></article>
    <article className="result-card context-card" data-result-part="3-post-context"><h3>{t.contextTitle}</h3><dl className="context-list"><div><dt>{t.author}</dt><dd>{context.author || t.notAvailable}</dd></div><div><dt>{t.postTime}</dt><dd>{context.timing || t.notAvailable}</dd></div><div><dt>{t.recency}</dt><dd>{context.recency || t.couldNotDetermine}</dd></div><div><dt>{t.checkedMaterial}</dt><dd>{friendlyCheckedMaterial(context.checked_material, language) || t.notAvailable}</dd></div></dl>{originalPost && <p><a href={originalPost} target="_blank" rel="noopener noreferrer">{t.openPost}</a></p>}{postLinks.length > 0 && <details><summary>{t.postLinks}</summary><ul>{postLinks.map(url => <li key={url}><a href={url} target="_blank" rel="noopener noreferrer">{url}</a></li>)}</ul></details>}</article>
    <section className="result-card" data-result-part="4-related-sources"><h3>{t.related}</h3><p>{t.relatedHelp}</p><SourceStatus result={result} sourceState={sourceState} t={t} onFindSources={onFindSources} /></section>
    <details className="result-card analyzed-card" data-result-part="5-analyzed-text"><summary>{t.analyzed}</summary><p className="small">{t.analyzedHelp}</p><p className="input-preview full-text">{result.analyzed_text}</p></details>
    <p className="friendly-reminder" data-result-part="6-reminder">{t.reminder}</p>
    <button type="button" className="primary result-check-again" data-result-part="7-check-again" onClick={onCheckAgain}>{t.checkAgain}</button>
  </section>;
}

export default function Popup() {
  const [text, setText] = useState(''), [page, setPage] = useState(EMPTY_PAGE), [file, setFile] = useState(null), [kind, setKind] = useState('image');
  const [status, setStatus] = useState('idle'), [error, setError] = useState(''), [result, setResult] = useState(null), [sourceState, setSourceState] = useState('idle');
  const [lookup, setLookup] = useState(true), [enabled, setEnabled] = useState(true), [language, setLanguage] = useState('en');
  const [consent, setConsent] = useState(false), [candidateState, setCandidateState] = useState('idle');
  const lock = useRef(false), sourceLock = useRef(false), candidateLock = useRef(false), textRef = useRef(null); const busy = !['idle', 'completed', 'failed'].includes(status); const t = copy[language];
  useEffect(() => { chrome.storage.local.remove(['suriphLastResult', 'suriphLastText', 'suriphLastPage', 'suriphReceipts']); chrome.storage.local.get({ suriphEnabled: true, suriphRetrieveSources: true, suriphLanguage: 'en' }, saved => { setEnabled(saved.suriphEnabled); setLookup(saved.suriphRetrieveSources); setLanguage(saved.suriphLanguage === 'tl' ? 'tl' : 'en'); }); }, []);
  const changeLanguage = next => { setLanguage(next); chrome.storage.local.set({ suriphLanguage: next }); };
  const clearResult = () => { setResult(null); setError(''); setStatus('idle'); setSourceState('idle'); setConsent(false); setCandidateState('idle'); sourceLock.current = false; candidateLock.current = false; };
  const checkAgain = () => { clearResult(); requestAnimationFrame(() => textRef.current?.focus()); };
  async function perform(nextStatus, action) { if (lock.current) return; lock.current = true; setStatus(nextStatus); setError(''); setResult(null); setSourceState('idle'); setConsent(false); setCandidateState('idle'); try { await action(); setStatus('completed'); } catch (reason) { setError(localizedError(reason.message, language, t)); setStatus('failed'); } finally { lock.current = false; } }
  async function extract(mode) { await perform(t.reading, async () => { const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true }); if (!tab?.id || !/^https:\/\/([^/]+\.)?facebook\.com\//i.test(tab.url || '')) throw new Error(t.noTab); const response = await chrome.tabs.sendMessage(tab.id, { type: 'SURIPH_EXTRACT', mode }); if (!response?.ok || !response.text?.trim()) throw new Error(response?.error || t.noText); setText(response.text); setPage({ url: tab.url, title: tab.title, context: response.context || null, postText: response.mode === 'post' ? response.text : '' }); }); }
  async function runText() { await perform(t.analyzing, async () => { if (!text.trim()) throw new Error(t.enter); setResult(await analyzeText({ text, pageUrl: page.url, pageTitle: page.title, context: page.context, retrieveSources: lookup })); }); }
  async function runMedia() { await perform(t.mediaBusy, async () => { if (!file) throw new Error(t.noFile); const output = await analyzeMedia(kind, file, { ...page, retrieveSources: lookup }); setText(output.analyzed_text); setResult(output); }); }
  async function findSources() { if (!result || sourceLock.current) return; sourceLock.current = true; setSourceState('loading'); try { const refreshed = await analyzeText({ text: result.analyzed_text, pageUrl: result.page_url, pageTitle: result.page_title, context: result.context, retrieveSources: true }); setResult(refreshed); setSourceState('completed'); setLookup(true); chrome.storage.local.set({ suriphRetrieveSources: true }); } catch { setSourceState('failed'); } finally { sourceLock.current = false; } }
  async function submitCurrentCandidate() { if (!consent || !result || candidateLock.current || candidateState === 'submitted') return; candidateLock.current = true; setCandidateState('submitting'); try { await submitCandidate({ text: result.analyzed_text, pageUrl: result.page_url || page.url, pageTitle: result.page_title || page.title, consentToStore: true }); setCandidateState('submitted'); } catch { candidateLock.current = false; setCandidateState('failed'); } }
  async function setPageTools(next) { setEnabled(next); await chrome.storage.local.set({ suriphEnabled: next }); const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true }); if (tab?.id && /^https:\/\/([^/]+\.)?facebook\.com\//i.test(tab.url || '')) await chrome.tabs.reload(tab.id); }
  return <main className="popup-shell"><header className="brand-row"><div><h1>SuriPH</h1><p>{t.tagline}</p></div><button type="button" className="page-tools-toggle" role="switch" aria-checked={enabled} disabled={busy} onClick={() => setPageTools(!enabled)} title={t.toggleTitle}><span className="toggle-label">{t.pageTools}</span><span className="toggle-track" aria-hidden="true"><span className="toggle-knob" /></span><strong>{enabled ? t.on : t.off}</strong></button></header>
    {!result && <LanguageSwitch language={language} onChange={changeLanguage} />}
    {!result && <><section className="result-card input-card"><label htmlFor="screen-text">{t.textLabel}</label><p>{t.inputHelp}</p><textarea ref={textRef} id="screen-text" rows={6} value={text} disabled={busy} onChange={event => { setText(event.target.value); setPage(EMPTY_PAGE); clearResult(); }} placeholder={t.placeholder} /><div className="button-row"><button className="secondary" disabled={busy} onClick={() => extract('selection')}>{t.selected}</button><button className="secondary" disabled={busy} onClick={() => extract('post')}>{t.caption}</button></div><fieldset disabled={busy} className="choices"><legend>{t.lookup}</legend><label><input type="checkbox" checked={lookup} onChange={event => { const next = event.target.checked; setLookup(next); chrome.storage.local.set({ suriphRetrieveSources: next }); clearResult(); }} />{t.lookupHelp}</label></fieldset><p className="small">{t.privacy}</p><button className="primary" disabled={busy} onClick={runText}>{t.analyze}</button></section>
    <details className="result-card"><summary>{t.mediaTitle}</summary><p>{t.mediaHelp}</p><label htmlFor="media-kind">{t.mediaType}</label><select id="media-kind" disabled={busy} value={kind} onChange={event => { setKind(event.target.value); setFile(null); clearResult(); }}><option value="image">{t.image}</option><option value="video">{t.video}</option></select><label htmlFor="media-file">{t.choose}</label><input key={kind} id="media-file" disabled={busy} type="file" accept={kind === 'image' ? 'image/*' : 'video/*'} onChange={event => { setFile(event.target.files?.[0] || null); clearResult(); }} /><button className="secondary full-width" disabled={busy || !file} onClick={runMedia}>{t.extract} {kind === 'image' ? t.image : t.video}</button></details></>}
    <div aria-live="polite" role="status">{busy && <p className="notice">{status}… {t.keepOpen}</p>}</div>{error && <p role="alert" className="error">{error}</p>}{!result && !busy && !error && <p className="empty-state">{t.empty}</p>}
    <Result result={result} language={language} onLanguageChange={changeLanguage} sourceState={sourceState} onFindSources={findSources} onCheckAgain={checkAgain} consent={consent} setConsent={setConsent} candidateState={candidateState} onSubmitCandidate={submitCurrentCandidate} />
    {!result && <footer><button className="text-button" disabled={busy} onClick={() => { setText(''); setPage(EMPTY_PAGE); setFile(null); clearResult(); }}>{t.clear}</button></footer>}
  </main>;
}
