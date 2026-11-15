import React, { useEffect, useRef, useState } from 'react';
import { BookOpen, CircleCheck, FileText, Info, ScanText, ShieldCheck, TriangleAlert } from 'lucide-react';
import { analyzeMedia, analyzeText, confirmVideoReview, lookupRelatedSources, submitCandidate } from './api.js';
import { checkedMaterialLabel, mergeRelatedSources, incompleteVideoNotice, displayPostDate, displayPostRecency } from './result_updates.js';

const EMPTY_PAGE = { url: '', title: '', context: null, postText: '' };
const EXTENSION_VERSION = globalThis.chrome?.runtime?.getManifest?.().version || 'unavailable';
const copy = {
  en: {
    tagline: 'Read carefully. Check the context.', pageTools: 'Page tools', on: 'on', off: 'off', toggleTitle: 'Turn SuriPH page controls on or off and reload Facebook',
    textLabel: 'Text to check', inputHelp: 'Review the complete public Facebook text before checking it. SuriPH does not save it by default.', placeholder: 'Paste English, Filipino or Taglish text…', selected: 'Use selected text', caption: 'Use Facebook post caption', lookup: 'Check reliable sources', lookupHelp: 'Look for related news reports and fact-checks that can help assess the post.', privacy: 'Do not submit private or identifying content.', analyze: 'Check text', mediaTitle: 'Check an image or video', mediaHelp: 'Review the text found in the media before relying on the result.', mediaType: 'Media type', image: 'Text in an image', video: 'Speech and text in a video', choose: 'Choose a file (maximum 50 MiB)', extract: 'Extract and check', clear: 'Clear input', empty: 'Your result and related sources will appear here.',
    reading: 'Reading selected Facebook content', analyzing: 'Checking sources', mediaBusy: 'Extracting media and checking sources', keepOpen: 'Please keep this popup open.', noTab: 'Open Facebook in the active tab first.', noText: 'No readable Facebook post text was found. Select the exact text or paste it here.', enter: 'Enter or select text before analyzing.', noFile: 'Choose a file first.', unavailable: 'The screening service is unavailable. Try again later.',
    prediction: 'SuriPH RESULT', why: 'Why this result', textClear: 'The text check did not find enough warning signs to flag this post.', textWarning: 'The text check found warning signs that may indicate misleading information.', scoreTitle: 'Misleading model score', scoreHelp: 'This model score is not the chance that the claim is false. Only claim-specific evidence from readable articles can change the final label.', features: 'How the text was analyzed', featuresHelp: 'These measurements describe the writing style and language. They do not prove by themselves that a post is true or false.',
    contextTitle: 'About this post', author: 'Posted by', postTime: 'Post date', recency: 'How recent', checkedMaterial: 'Content checked', postLinks: 'Other links included in the post', postLinksHelp: 'These links came from the post and were not checked as evidence.', searchPreview: 'Search result preview only; the article could not be read, so this is not verified evidence.', searchSnippet: 'Search preview (not verified)', notAvailable: 'Not available', couldNotDetermine: 'Could not determine', openPost: 'Open original post',
    related: 'Sources found', relatedHelp: 'A link or search preview does not verify the full claim. Only readable article content is assessed; compare its details with the post.', findSources: 'Find related sources', findingSources: 'Finding related sources…', lookupOff: 'Source search was not requested.', noRelated: 'No closely related source was found.', lookupUnavailable: 'Source search is temporarily unavailable.', lookupFailed: 'The source search could not be completed.', missingLinks: 'This alone does not mean the post is misleading.', publisherMissing: 'Source not listed', factCheckRating: 'Fact-check rating',
    analyzed: 'Text checked', analyzedHelp: 'This is the exact text SuriPH checked.',
    reminder: 'SuriPH can make mistakes. Read the full post, check its date and source, and compare it with reliable references before sharing or acting on it.',
    checkAgain: 'Check again', nextHelp: 'Optionally submit this exact text to the private candidate-review queue for human review.', consent: 'I consent to storing this analyzed text and page metadata for human review. It will not enter a dataset automatically.', submit: 'Submit for human review', submitting: 'Submitting…', submitted: 'Submitted for human review.', candidateError: 'The candidate could not be submitted.',
  },
  tl: {
    tagline: 'Basahing mabuti. Suriin ang konteksto.', pageTools: 'Mga kontrol sa page', on: 'on', off: 'off', toggleTitle: 'I-on o i-off ang mga kontrol ng SuriPH at i-reload ang Facebook',
    textLabel: 'Tekstong susuriin', inputHelp: 'Basahin muna ang buong pampublikong Facebook text. Hindi ito sine-save ng SuriPH bilang default.', placeholder: 'I-paste ang English, Filipino, o Taglish na teksto…', selected: 'Gamitin ang piniling teksto', caption: 'Gamitin ang caption ng Facebook post', lookup: 'Suriin ang mapagkakatiwalaang sources', lookupHelp: 'Maghanap ng kaugnay na balita at fact-checks na makatutulong sa pagsusuri ng post.', privacy: 'Huwag magsumite ng pribado o makakakilalang impormasyon.', analyze: 'Suriin ang teksto', mediaTitle: 'Suriin ang image o video', mediaHelp: 'Basahin ang tekstong nakuha mula sa media bago umasa sa resulta.', mediaType: 'Uri ng media', image: 'Teksto sa image', video: 'Salita at teksto sa video', choose: 'Pumili ng file (hanggang 50 MiB)', extract: 'Kunin at suriin', clear: 'Burahin ang input', empty: 'Dito lalabas ang resulta at mga kaugnay na sources.',
    reading: 'Binabasa ang piniling Facebook content', analyzing: 'Naghahanap ng ebidensiya', mediaBusy: 'Kinukuha ang media at naghahanap ng ebidensiya', keepOpen: 'Panatilihing bukas ang popup.', noTab: 'Buksan muna ang Facebook sa aktibong tab.', noText: 'Walang nakitang mababasang Facebook post text. Piliin ang eksaktong teksto o i-paste ito rito.', enter: 'Maglagay o pumili muna ng teksto.', noFile: 'Pumili muna ng file.', unavailable: 'Hindi magamit ang screening service. Subukan muli mamaya.',
    prediction: 'RESULTA NG SURIPH', why: 'Bakit ito ang resulta', textClear: 'Walang sapat na warning signs na nakita sa pagsusuri ng teksto.', textWarning: 'May nakitang warning signs sa teksto na maaaring nagpapahiwatig ng misleading na impormasyon.', scoreTitle: 'Model score para sa Misleading', scoreHelp: 'Hindi ito posibilidad na mali ang claim. Tanging ebidensiyang direktang tumutukoy sa claim mula sa nababasang artikulo ang maaaring magbago sa final label.', features: 'Paano sinuri ang teksto', featuresHelp: 'Inilalarawan ng mga sukat na ito ang paraan ng pagkakasulat at paggamit ng wika. Hindi nila pinatutunayan nang mag-isa kung totoo o mali ang post.',
    contextTitle: 'Tungkol sa post', author: 'Nag-post', postTime: 'Petsa ng post', recency: 'Gaano kabago', checkedMaterial: 'Sinuring content', postLinks: 'Iba pang link na kasama sa post', postLinksHelp: 'Galing sa post ang mga link na ito at hindi sinuri bilang ebidensiya.', searchPreview: 'Search result preview lang ito; hindi mabasa ang artikulo kaya hindi ito beripikadong ebidensiya.', searchSnippet: 'Search preview (hindi beripikado)', notAvailable: 'Hindi available', couldNotDetermine: 'Hindi matukoy', openPost: 'Buksan ang orihinal na post',
    related: 'Mga nahanap na source', relatedHelp: 'Hindi patunay sa buong claim ang link o search preview. Sinusuri lang ang nababasang laman ng artikulo; ihambing ang mga detalye nito sa post.', findSources: 'Maghanap ng kaugnay na sources', findingSources: 'Naghahanap ng kaugnay na sources…', lookupOff: 'Hindi hiniling ang paghahanap ng sources.', noRelated: 'Walang nakitang malapit na kaugnay na source.', lookupUnavailable: 'Pansamantalang hindi magamit ang paghahanap ng sources.', lookupFailed: 'Hindi nakumpleto ang paghahanap ng sources.', missingLinks: 'Hindi nito awtomatikong ibig sabihin na misleading ang post.', publisherMissing: 'Hindi nakalagay ang source', factCheckRating: 'Rating ng fact-check',
    analyzed: 'Tekstong sinuri', analyzedHelp: 'Ito ang eksaktong tekstong sinuri ng SuriPH.',
    reminder: 'Maaaring magkamali ang SuriPH. Basahin ang buong post, tingnan ang petsa at pinagmulan, at ikumpara ito sa mapagkakatiwalaang sanggunian bago ibahagi o aksyunan.',
    checkAgain: 'Suriin muli', nextHelp: 'Opsyonal na isumite ang eksaktong teksto sa pribadong candidate-review queue para sa human review.', consent: 'Pumapayag akong i-store ang sinuring teksto at page metadata para sa human review. Hindi ito awtomatikong isasama sa dataset.', submit: 'Isumite para sa human review', submitting: 'Isinusumite…', submitted: 'Naisumite para sa human review.', candidateError: 'Hindi naisumite ang candidate.',
  },
};

const safeUrl = value => { try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) ? url.href : null; } catch { return null; } };
const displayLabel = result => result?.internal_label === 'Misleading' ? 'Potentially Misleading' : 'No Misleading Information Detected';
const friendlyReason = (result, t) => {
  if (result.decision_source === 'verified_evidence') return result.evidence_relationship === 'supports'
    ? (t === copy.tl ? 'May nabasang ebidensiyang sumusuporta sa buong claim at konteksto nito.' : 'Readable evidence supports the complete claim and its context.')
    : (t === copy.tl ? 'May nabasang source na direktang sumasalungat sa buong claim.' : 'A readable source directly contradicts the complete claim.');
  if (result.evidence_relationship === 'conflicting') return t === copy.tl
    ? 'May nabasang source na sumusuporta at may sumasalungat sa claim. Hindi nalutas ang salungatan; hindi beripikado ang model result.'
    : 'Readable sources both support and contradict this claim. The conflict is unresolved; the model result is unverified.';
  if (result.evidence_relationship === 'contradicts') return t === copy.tl
    ? 'May nababasang source na sumasalungat sa claim, pero kailangan ng sapat na ebidensiyang tumutukoy sa mismong claim para baguhin ang label. Model result pa rin ito at hindi beripikadong verdict.'
    : 'A readable source contradicts the claim, but sufficient claim-specific evidence is required to change the label. The result remains an unverified model output.';
  if (Number(result.supporting_source_count) > 0) return t === copy.tl
    ? 'May nababasang mapagkakatiwalaang source na sumusuporta, pero kailangan pang pumasa ang ebidensiya sa pagsusuri ng claim at pinagmulan, nang walang mapagkakatiwalaang salungatan. Model result pa rin ito, hindi factual verdict.'
    : 'A readable trusted article appears to support the claim, but the evidence must meet the claim-specific authority or independent-publisher checks without a trusted contradiction. The result remains an unverified model output, not a factual verdict.';
  if ((result.related_sources || []).length > 0) return t === copy.tl
    ? 'May kaugnay na link sa ibaba, pero walang nababasang source na direktang nagpatunay sa buong claim. Hindi beripikado ang model result.'
    : 'The links below are related or unreadable; no readable source established the complete claim. The model result is unverified.';
  if (result.screening_mode === 'evidence_only') return t === copy.tl
    ? 'Hindi pa beripikado ang claim. Kailangan pa ng sapat na mapagkakatiwalaang sources o human review.'
    : 'This claim is not verified yet. More reliable sources or human review are needed.';
  const reason = result.internal_label === 'Misleading' ? t.textWarning : t.textClear;
  return `${reason} ${t === copy.tl ? 'Hindi pa verified ang resultang ito gamit ang sapat na ebidensiya; model prediction ito.' : 'This result is not verified by sufficient evidence; it is a model prediction.'}`;
};
const featureHelp = (name, language) => ({
  code_switching_ratio: language === 'tl' ? 'Paghahalo ng Filipino at English.' : 'Mixing Filipino and English.',
  filipino_particle_frequency: language === 'tl' ? 'Paggamit ng karaniwang katagang Filipino.' : 'Use of common Filipino connector words.',
  punctuation_intensity: language === 'tl' ? 'Paggamit ng tandang padamdam at pananong.' : 'Use of exclamation and question marks.',
  capitalization_ratio: language === 'tl' ? 'Paggamit ng MALALAKING TITIK.' : 'Use of CAPITAL LETTERS.',
  repeated_character_ratio: language === 'tl' ? 'Paulit-ulit na letra gaya ng “grabeeee”.' : 'Repeated letters such as “wowwww”.',
  emotional_language_frequency: language === 'tl' ? 'Mga salitang nagpapahayag ng matinding emosyon.' : 'Words that express strong emotion.',
  urgency_cue_frequency: language === 'tl' ? 'Mga salitang nag-uudyok na kumilos agad.' : 'Words that urge readers to act quickly.',
}[name] || '');
const percent = value => Number.isFinite(value) ? `${(value * 100).toFixed(2)}%` : '—';
const localizedError = (message, language, t) => {
  if (language === 'en' || !message) return message || t.unavailable;
  if (/speech.*clearly|speech quality|uncertain transcript/i.test(message)) return 'Hindi malinaw ang ilang salita sa audio kaya walang ginawang prediction. Gumamit ng mas malinaw na clip o piliin ang buong caption.';
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
  const checkedUrls = new Set(sources.filter(source => source.content_status === 'readable').map(source => safeUrl(source.url)).filter(Boolean));
  const postLinks = [...new Set((result.context_explanation?.relevant_links || []).map(safeUrl).filter(Boolean))]
    .filter(url => !checkedUrls.has(url));
  const postLinksContent = postLinks.length > 0 && <div className="post-source-links"><h4>{t.postLinks}</h4><p className="small">{t.postLinksHelp}</p><ul>{postLinks.map(url => <li key={url}><a href={url} target="_blank" rel="noopener noreferrer">{url}</a></li>)}</ul></div>;
  const relationshipText = source => source.relationship === 'supports' && source.decision_eligible === false
    ? (t === copy.tl ? 'May kaugnay na suportang konteksto, pero hindi sapat para baguhin ang label.' : 'Supporting context was found, but it is insufficient to change the label.')
    : t === copy.tl
    ? source.relationship === 'supports' ? 'Sinusuportahan ang buong claim' : source.relationship === 'contradicts' ? 'Sumasalungat sa buong claim' : source.content_status === 'inaccessible' ? 'Hindi mabasa ang artikulo; walang nakuhang excerpt' : 'Kaugnay na balita; hindi pa napatunayan ang claim'
    : source.relationship === 'supports' ? 'Supports the complete claim' : source.relationship === 'contradicts' ? 'Contradicts the complete claim' : source.content_status === 'inaccessible' ? 'Article inaccessible; no article excerpt available' : 'Related coverage; claim not established';
  if (factChecks.length || sources.length) return <>{postLinksContent}{factChecks.map(source => <article className="source" key={source.url}><a href={safeUrl(source.url)} target="_blank" rel="noopener noreferrer">{source.title || source.claim}</a><p>{source.publisher || t.publisherMissing} · {t.factCheckRating}: <strong>{source.rating}</strong></p></article>)}{sources.map(source => {
    const inaccessible = source.content_status === 'inaccessible';
    const title = inaccessible ? source.search_title || source.url : source.title || (t === copy.tl ? 'Buksan ang source article' : 'Open source article');
    return <article className="source" key={source.url}><a href={safeUrl(source.url)} target="_blank" rel="noopener noreferrer">{title}</a><p>{source.source || t.publisherMissing}{source.date ? ` · ${source.date}` : ''}</p>{inaccessible && <p className="small">{t.searchPreview}</p>}{inaccessible && source.search_snippet && <p className="small"><strong>{t.searchSnippet}:</strong> {source.search_snippet}</p>}{!inaccessible && source.snippet && <p>{source.snippet}</p>}<p>{source.relationship === 'conflicting' ? (t === copy.tl ? 'May magkasalungat na pahayag sa artikulo; hindi ginamit para baguhin ang label.' : 'Conflicting assertions in this article; not used to change the label.') : relationshipText(source)}</p>{!inaccessible && source.evidence_excerpt && <details><summary>{t === copy.tl ? 'Basahin ang kaugnay na sipi' : 'Read the matching passage'}</summary><blockquote style={{ whiteSpace: 'pre-wrap', margin: '8px 0', paddingLeft: 12, borderLeft: '3px solid #0f766e' }}>{source.evidence_excerpt}</blockquote>{source.used_for_decision && <p className="small">{t === copy.tl ? 'Ginamit sa final label; ihambing ang siping ito sa orihinal na post.' : 'Used for the final label; compare this passage with the original post.'}</p>}</details>}</article>;
  })}</>;
  const message = status === 'not_requested' ? t.lookupOff : status === 'no_results' ? t.noRelated : status === 'failed' ? t.lookupFailed : t.lookupUnavailable;
  return <>{postLinksContent}<p className="notice">{message} {t.missingLinks}</p>{status === 'not_requested' && <button type="button" className="secondary full-width" onClick={onFindSources}>{t.findSources}</button>}</>;
}

function ExtractedText({ result, language }) {
  const extraction = result.extraction;
  if (!extraction) return <p className="input-preview full-text">{result.analyzed_text}</p>;
  const tl = language === 'tl';
  const parts = [
    [tl ? 'Caption ng post' : 'Post caption', extraction.caption_text],
    [tl ? 'Mga salitang narinig sa video' : 'Speech heard in the video', extraction.transcript_text],
    [tl ? 'Tekstong nakita sa mga frame' : 'Text found in sampled video frames', extraction.frame_ocr_text],
    [tl ? 'Tekstong nakita sa image' : 'Text found in the image', extraction.ocr_text],
  ];
  return <>
    {incompleteVideoNotice(extraction, language) && <p className="error">{incompleteVideoNotice(extraction, language)}</p>}
    {parts.filter(([, text]) => text?.trim()).map(([label, text]) => <div key={label}><h4>{label}</h4><p className="input-preview full-text">{text}</p></div>)}
    {extraction.frame_ocr_included === false && extraction.frame_ocr_text && <p className="small">{tl ? 'Ipinakita ang text sa frame para masuri mo, pero hindi ito isinama sa prediction dahil hindi matiyak na kaugnay ito ng audio.' : 'Frame text is shown for your review but was excluded from the prediction because its connection to the speech could not be established.'}</p>}
    {Array.isArray(extraction.frame_ocr_regions) && extraction.frame_ocr_regions.length > 0 && <details><summary>{tl ? 'Teksto ayon sa oras ng frame' : 'Frame text by timestamp'}</summary>{extraction.frame_ocr_regions.filter(region => region.text).map((region, index) => <p className="input-preview full-text" key={`${region.sample_seconds}-${index}`}>{Number(region.sample_seconds || 0).toFixed(1)}s: {region.text}</p>)}</details>}
    {'transcript_text' in extraction && !extraction.transcript_text && <p className="small">{tl ? 'Walang malinaw na salita na nakuha mula sa audio. Hindi pinunan ng gawa-gawang transcript.' : 'No reliable speech was extracted from the audio. No transcript was invented.'}</p>}
    {extraction.quality_notice && <p className="small">{tl ? 'Ihambing ang nakuha sa orihinal na video. Maaaring may maling salita o hindi nakuha; piling video frames lang ang sinuri.' : 'Compare the extracted text with the original video. Words may be missed or misread; only sampled frames were checked.'}</p>}
    {extraction.discarded_ocr_detections > 0 && <p className="small">{tl ? 'Hindi isinama ang ilang tekstong hindi malinaw basahin.' : 'Some low-confidence image text was excluded.'}</p>}
    <details><summary>{tl ? 'Pinagsamang tekstong sinuri' : 'Combined text used for the check'}</summary><p className="input-preview full-text">{result.analyzed_text}</p></details>
  </>;
}

export function Result({ result, language = 'en', onLanguageChange = () => {}, sourceState = 'idle', onFindSources = () => {}, onCheckAgain = () => {} }) {
  if (!result) return null;
  const t = copy[language]; const context = result.context_explanation || {};
  const originalPost = safeUrl(context.original_post_url);
  return <section className="result-stack" aria-label="Analysis result"><LanguageSwitch language={language} onChange={onLanguageChange} />
    <article className={`result-card prediction-card ${result.internal_label === 'Misleading' ? 'warning' : 'clear'}`} data-result-part="1-prediction"><span className="prediction-icon">{result.internal_label === 'Misleading' ? <TriangleAlert aria-hidden="true" /> : <CircleCheck aria-hidden="true" />}</span><div><p className="eyebrow">{t.prediction}</p><h2>{displayLabel(result)}</h2></div></article>
    <article className="result-card score-card" data-result-part="2-explanation"><h3><Info aria-hidden="true" />{t.why}</h3><p>{friendlyReason(result, t)}</p><p className="small">{result.screening_mode === 'evidence_only' ? (language === 'tl' ? 'Naka-off ang classifier. Evidence retrieval lang ang ginamit; hindi factual verdict ang hindi pa beripikadong warning.' : 'The classifier is off. This uses evidence retrieval only; an unverified warning is not a factual verdict.') : result.decision_source === 'verified_evidence' ? (language === 'tl' ? 'Ang final label ay batay sa nasuring artikulo; hiwalay ang model score.' : 'The final label follows assessed article evidence; the model score is separate.') : t.scoreHelp}</p></article>
    <article className="result-card context-card" data-result-part="3-post-context"><h3><FileText aria-hidden="true" />{t.contextTitle}</h3><dl className="context-list"><div><dt>{t.author}</dt><dd>{context.author || t.notAvailable}</dd></div><div><dt>{t.postTime}</dt><dd>{displayPostDate(context, language)}</dd></div><div><dt>{t.recency}</dt><dd>{displayPostRecency(context, language)}</dd></div><div><dt>{t.checkedMaterial}</dt><dd>{checkedMaterialLabel(context.checked_material, result.extraction, language) || t.notAvailable}</dd></div></dl>{originalPost && <p><a href={originalPost} target="_blank" rel="noopener noreferrer">{t.openPost}</a></p>}</article>
    <details className="result-card" data-result-part="4-features"><summary><ScanText aria-hidden="true" />{t.features}</summary>{result.screening_mode === 'evidence_only' ? <p>{language === 'tl' ? 'Naka-off ang text classifier. Ipinapakita sa ibaba kung anong teksto ang nakuha mula sa caption, image, o video.' : 'The text classifier is off. The extracted caption, image, or video text is shown below.'}</p> : <><p>{t.featuresHelp}</p><p>{language === 'tl' ? 'Orihinal na model label' : 'Original model label'}: {result.model_public_label || displayLabel(result)} · {t.scoreTitle}: {percent(Number(result.model_score))}</p><p className="small">{t.scoreHelp}</p><dl className="feature-list">{result.linguistic_indicators?.map(item => <div key={item.name} data-feature={item.name} data-value={item.value}><dt>{language === 'tl' ? item.display_name_tagalog : item.display_name} <strong>{percent(Number(item.value))}</strong></dt><dd>{featureHelp(item.name, language)}</dd></div>)}</dl></>}</details>
    <section className="result-card" data-result-part="5-related-sources"><h3><BookOpen aria-hidden="true" />{t.related}</h3><p>{result.decision_source === 'verified_evidence' ? (language === 'tl' ? 'Sinuri ang buong mababasang artikulo at inihambing ang claim at konteksto.' : 'Readable article bodies were compared with the complete claim and context.') : t.relatedHelp}</p><SourceStatus result={result} sourceState={sourceState} t={t} onFindSources={onFindSources} /></section>
    <details className="result-card analyzed-card" data-result-part="6-analyzed-text"><summary><ScanText aria-hidden="true" />{t.analyzed}</summary><p className="small">{t.analyzedHelp}</p><ExtractedText result={result} language={language} /></details>
    <p className="friendly-reminder" data-result-part="7-reminder"><Info aria-hidden="true" />{t.reminder}</p>
    <button type="button" className="primary result-check-again" data-result-part="8-check-again" onClick={onCheckAgain}>{t.checkAgain}</button>
  </section>;
}

export default function Popup() {
  const [text, setText] = useState(''), [page, setPage] = useState(EMPTY_PAGE), [file, setFile] = useState(null), [kind, setKind] = useState('image');
  const [status, setStatus] = useState('idle'), [error, setError] = useState(''), [result, setResult] = useState(null), [sourceState, setSourceState] = useState('idle');
  const [lookup, setLookup] = useState(true), [enabled, setEnabled] = useState(true), [language, setLanguage] = useState('en');
  const [consent, setConsent] = useState(false), [candidateState, setCandidateState] = useState('idle');
  const [videoReview, setVideoReview] = useState(null);
  const lock = useRef(false), sourceLock = useRef(false), candidateLock = useRef(false), textRef = useRef(null), requestGeneration = useRef(0); const busy = !['idle', 'completed', 'failed'].includes(status); const t = copy[language];
  useEffect(() => {
    chrome.storage.local.remove(['suriphLastResult', 'suriphLastText', 'suriphLastPage', 'suriphReceipts']);
    chrome.storage.local.get({ suriphEnabled: true, suriphRetrieveSources: true, suriphLanguage: 'en' }, saved => { setEnabled(saved.suriphEnabled); setLookup(saved.suriphRetrieveSources); setLanguage(saved.suriphLanguage === 'tl' ? 'tl' : 'en'); });
    chrome.tabs.query({ active: true, lastFocusedWindow: true }, ([tab]) => {
      if (!tab?.id || !/^https:\/\/([^/]+\.)?facebook\.com\//i.test(tab.url || '')) return;
      chrome.tabs.sendMessage(tab.id, { type: 'SURIPH_RESCAN_CONTROLS' }, () => void chrome.runtime.lastError);
    });
  }, []);
  const changeLanguage = next => { setLanguage(next); chrome.storage.local.set({ suriphLanguage: next }); };
  const clearResult = () => { requestGeneration.current += 1; setResult(null); setVideoReview(null); setError(''); setStatus('idle'); setSourceState('idle'); setConsent(false); setCandidateState('idle'); sourceLock.current = false; candidateLock.current = false; };
  const checkAgain = () => { clearResult(); requestAnimationFrame(() => textRef.current?.focus()); };
  async function perform(nextStatus, action) { if (lock.current) return; lock.current = true; setStatus(nextStatus); setError(''); setResult(null); setSourceState('idle'); setConsent(false); setCandidateState('idle'); try { await action(); setStatus('completed'); } catch (reason) { setError(localizedError(reason.message, language, t)); setStatus('failed'); } finally { lock.current = false; } }
  async function extract(mode) { await perform(t.reading, async () => { const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true }); if (!tab?.id || !/^https:\/\/([^/]+\.)?facebook\.com\//i.test(tab.url || '')) throw new Error(t.noTab); const response = await chrome.tabs.sendMessage(tab.id, { type: 'SURIPH_EXTRACT', mode }); if (!response?.ok || !response.text?.trim()) throw new Error(response?.error || t.noText); setText(response.text); setPage({ url: tab.url, title: tab.title, context: response.context || null, postText: response.mode === 'post' ? response.text : '' }); }); }
  async function runText() { await perform(t.analyzing, async () => { if (!text.trim()) throw new Error(t.enter); setResult(await analyzeText({ text, pageUrl: page.url, pageTitle: page.title, context: page.context, retrieveSources: lookup })); }); }
  async function runMedia() { await perform(t.mediaBusy, async () => { if (!file) throw new Error(t.noFile); const output = await analyzeMedia(kind, file, { ...page, retrieveSources: lookup }); if (kind === 'video') setVideoReview(output); else { setText(output.analyzed_text); setResult(output); } }); }
  async function confirmVideo() { if (!videoReview || lock.current) return; await perform(t.analyzing, async () => { try { const output = await confirmVideoReview(videoReview); setVideoReview(null); setText(output.analyzed_text); setResult(output); } catch (reason) { setVideoReview(null); throw reason; } }); }
  async function findSources() {
    if (!result || sourceLock.current) return;
    const requestedResult = result, generation = requestGeneration.current;
    sourceLock.current = true; setSourceState('loading');
    try {
      const sources = await lookupRelatedSources({ text: requestedResult.analyzed_text, pageUrl: requestedResult.page_url });
      if (generation !== requestGeneration.current) return;
      setResult(current => mergeRelatedSources(current, requestedResult, sources));
      setSourceState('completed'); setLookup(true);
      chrome.storage.local.set({ suriphRetrieveSources: true });
    } catch {
      if (generation === requestGeneration.current) setSourceState('failed');
    } finally {
      if (generation === requestGeneration.current) sourceLock.current = false;
    }
  }
  async function submitCurrentCandidate() { if (!consent || !result || candidateLock.current || candidateState === 'submitted') return; candidateLock.current = true; setCandidateState('submitting'); try { await submitCandidate({ text: result.analyzed_text, pageUrl: result.page_url || page.url, pageTitle: result.page_title || page.title, consentToStore: true }); setCandidateState('submitted'); } catch { candidateLock.current = false; setCandidateState('failed'); } }
  async function setPageTools(next) { setEnabled(next); await chrome.storage.local.set({ suriphEnabled: next }); const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true }); if (tab?.id && /^https:\/\/([^/]+\.)?facebook\.com\//i.test(tab.url || '')) await chrome.tabs.reload(tab.id); }
  return <main className="popup-shell"><header className="brand-row"><div className="brand-identity"><span className="brand-mark"><ShieldCheck aria-hidden="true" /></span><div><h1>SuriPH <span className="version-label">v{EXTENSION_VERSION}</span></h1><p>{t.tagline}</p></div></div><button type="button" className="page-tools-toggle" role="switch" aria-checked={enabled} disabled={busy} onClick={() => setPageTools(!enabled)} title={t.toggleTitle}><span className="toggle-label">{t.pageTools}</span><span className="toggle-track" aria-hidden="true"><span className="toggle-knob" /></span><strong>{enabled ? t.on : t.off}</strong></button></header>
    {!result && <LanguageSwitch language={language} onChange={changeLanguage} />}
    {!result && <><section className="result-card input-card"><label htmlFor="screen-text">{t.textLabel}</label><p>{t.inputHelp}</p><textarea ref={textRef} id="screen-text" rows={6} value={text} disabled={busy} onChange={event => { setText(event.target.value); setPage(EMPTY_PAGE); clearResult(); }} placeholder={t.placeholder} /><div className="button-row"><button className="secondary" disabled={busy} onClick={() => extract('selection')}>{t.selected}</button><button className="secondary" disabled={busy} onClick={() => extract('post')}>{t.caption}</button></div><fieldset disabled={busy} className="choices"><legend>{t.lookup}</legend><label><input type="checkbox" checked={lookup} onChange={event => { const next = event.target.checked; setLookup(next); chrome.storage.local.set({ suriphRetrieveSources: next }); clearResult(); }} />{t.lookupHelp}</label></fieldset><p className="small">{t.privacy}</p><button className="primary" disabled={busy} onClick={runText}>{t.analyze}</button></section>
    <details className="result-card"><summary>{t.mediaTitle}</summary><p>{t.mediaHelp}</p><label htmlFor="media-kind">{t.mediaType}</label><select id="media-kind" disabled={busy} value={kind} onChange={event => { setKind(event.target.value); setFile(null); clearResult(); }}><option value="image">{t.image}</option><option value="video">{t.video}</option></select><label htmlFor="media-file">{t.choose}</label><input key={kind} id="media-file" disabled={busy} type="file" accept={kind === 'image' ? 'image/*' : 'video/*'} onChange={event => { setFile(event.target.files?.[0] || null); clearResult(); }} /><button className="secondary full-width" disabled={busy || !file} onClick={runMedia}>{t.extract} {kind === 'image' ? t.image : t.video}</button></details></>}
    <div aria-live="polite" role="status">{busy && <p className="notice">{status}… {t.keepOpen}</p>}</div>{error && <p role="alert" className="error">{error}</p>}
    {videoReview && !result && <section className="result-card video-review"><h2>{language === 'tl' ? 'Suriin muna ang teksto sa video' : 'Review the video extraction'}</h2><p>{language === 'tl' ? 'Pakinggan ang video. Ihambing ang pangalan, lugar, petsa, halaga, pagtanggi, at paratang. Wala pang prediction.' : 'Listen to the video. Compare names, places, dates, amounts, negation, and allegations. No prediction has been made yet.'}</p>{videoReview.extraction?.speech_frame_agreement === 'review_required' && <p className="status error">{language === 'tl' ? 'Magkaiba ang mga salita sa audio at sa screen. Maaaring magkaiba ang wika nila. Ihambing ang dalawa sa video bago kumpirmahin.' : 'The speech and on-screen wording differ. They may use different languages. Compare both with the video before confirming.'}</p>}{incompleteVideoNotice(videoReview.extraction, language) && <p className="error">{incompleteVideoNotice(videoReview.extraction, language)}</p>}<h3>{language === 'tl' ? 'Salitang narinig' : 'Speech heard'}</h3><p className="input-preview">{videoReview.extraction?.transcript_text || '—'}</p><h3>{language === 'tl' ? 'Tekstong nasa screen' : 'On-screen text'}</h3><p className="input-preview">{videoReview.extraction?.frame_ocr_text || '—'}</p><div className="video-review-actions"><button className="secondary" disabled={busy} onClick={() => { setVideoReview(null); setError(language === 'tl' ? 'Mali ang nakuhang teksto. Walang prediction.' : 'The extracted text was rejected. No prediction was made.'); setStatus('failed'); }}>{language === 'tl' ? 'Mali ang teksto — walang prediction' : 'Text is wrong — no prediction'}</button><button className="primary" disabled={busy} onClick={confirmVideo}>{language === 'tl' ? 'Tugma ang teksto — suriin' : 'Text matches — analyze it'}</button></div></section>}
    {!result && !videoReview && !busy && !error && <p className="empty-state">{t.empty}</p>}
    <Result result={result} language={language} onLanguageChange={changeLanguage} sourceState={sourceState} onFindSources={findSources} onCheckAgain={checkAgain} consent={consent} setConsent={setConsent} candidateState={candidateState} onSubmitCandidate={submitCurrentCandidate} />
    {!result && <footer><button className="text-button" disabled={busy} onClick={() => { setText(''); setPage(EMPTY_PAGE); setFile(null); clearResult(); }}>{t.clear}</button></footer>}
  </main>;
}
