// Inject controls proactively; page content is read only after a user click.
const POST_SELECTORS = ['[role="article"]', 'article'];
const POST_TEXT_SELECTORS = [
  '[data-ad-comet-preview="message"]', '[data-ad-preview="message"]',
  '[data-ad-rendering-role="story_message"]', '[data-testid="post_message"]',
  '[data-testid="post-content"]',
];
const CONTROL_ATTRIBUTE = 'data-suriph-control';
let extensionEnabled = true;
let retrievalEnabled = false;
let interfaceLanguage = 'en';
let activeResultHost = null;

function rootsFrom(root = document) {
  const roots = [root];
  for (const element of root.querySelectorAll('*')) {
    if (element.id === 'suriph-control-host') continue;
    if (element.shadowRoot) roots.push(...rootsFrom(element.shadowRoot));
  }
  return roots;
}
function normalize(value) { return (value || '').replace(/\s+/g, ' ').trim(); }
function tr(english, tagalog) { return interfaceLanguage === 'tl' ? tagalog : english; }
function localizedError(message) {
  if (interfaceLanguage !== 'tl') return message || 'SuriPH could not complete the request.';
  if (/timed out|too long/i.test(message || '')) return 'Nag-timeout ang request. Subukan ang mas maikling content.';
  if (/video|media|capture|image|ocr|transcri/i.test(message || '')) return 'Hindi nakuha o naproseso ang media. Gamitin ang file upload kung kailangan.';
  if (/backend|service|unavailable|connection/i.test(message || '')) return 'Hindi magamit ang SuriPH service. Suriin ang backend at subukan muli.';
  return 'Hindi nakumpleto ng SuriPH ang request. Subukan muli.';
}
function findPosts() {
  const posts = [];
  for (const root of rootsFrom()) for (const selector of POST_SELECTORS) for (const element of root.querySelectorAll(selector)) if (!element.hasAttribute(CONTROL_ATTRIBUTE)) posts.push(element);
  const unique = [...new Set(posts)];
  return unique
    .filter((post) => {
      const text = normalize(post.innerText || post.textContent || '');
      if (post.closest('[role="dialog"], [role="complementary"], [aria-label*="chat" i], [aria-label*="conversation" i], [data-testid*="chat" i]')) return false;
      // Facebook search/group result cards are not posts and create visual clutter.
      if (/\bjoin\b/i.test(text) && /\bmembers?\b/i.test(text) && !/\bfollow\b/i.test(text)) return false;
      // Standalone comment rows expose role=article too; real post containers usually contain nested rows.
      if (post.matches('[role="article"]') && !post.querySelector('[role="article"]') && /\breply\b/i.test(text)) return false;
      return true;
    })
    // If selectors identify nested versions of one post, keep only the outer post container.
    .filter((post) => !unique.some((other) => other !== post && other.contains(post) && other.matches('article, [role="article"]')));
}
function collectPostText(post) {
  const parts = [];
  const add = (node) => {
    if (!node || node.closest?.('#suriph-control-host, button, [role="button"], nav, form')) return;
    const text = normalize(node.innerText || node.textContent || '');
    if (text) parts.push(text);
  };
  for (const selector of POST_TEXT_SELECTORS) {
    if (post.matches?.(selector)) add(post);
    post.querySelectorAll?.(selector).forEach(add);
  }
  const selected = [...new Set(parts)];
  if (selected.length) return normalize(selected.join(' '));

  // Fail closed when Facebook's recognized message containers are absent.
  // Reading the whole article/feed container can include menus, reactions and comments.
  return '';
}
function postForSelection() {
  const selection = window.getSelection();
  if (!selection?.rangeCount) return null;
  let node = selection.getRangeAt(0).commonAncestorContainer;
  if (node?.nodeType === Node.TEXT_NODE) node = node.parentElement;
  return node?.closest?.(POST_SELECTORS.join(',')) || null;
}
function postNearestViewport() {
  const activePost = document.activeElement?.closest?.(POST_SELECTORS.join(','));
  if (activePost) return activePost;
  const center = window.innerHeight / 2;
  return findPosts()
    .map(post => ({ post, rect: post.getBoundingClientRect() }))
    .filter(({ rect }) => rect.bottom > 0 && rect.top < window.innerHeight && rect.width > 0 && rect.height > 0)
    .sort((left, right) => Math.abs((left.rect.top + left.rect.bottom) / 2 - center) - Math.abs((right.rect.top + right.rect.bottom) / 2 - center))[0]?.post || null;
}
function collectPostContext(post) {
  const time = post.querySelector('time');
  const authorNode = post.querySelector('[data-ad-rendering-role="profile_name"], [role="link"] strong, h2, h3');
  const links = [...post.querySelectorAll('a[href]')].map((link) => link.href).filter((url) => /^https?:/i.test(url));
  const relativeNode = [...post.querySelectorAll('a, span, abbr')].find((node) => /^(just now|yesterday|\d+\s*(s|m|h|d|w)|edited)$/i.test(normalize(node.textContent || node.getAttribute('aria-label') || '')));
  const publishedAt = time?.dateTime || null;
  const publishedText = normalize(time?.textContent || relativeNode?.textContent || relativeNode?.getAttribute('aria-label') || '') || null;
  let freshness = 'Date unavailable';
  if (publishedAt) { const age = Date.now() - new Date(publishedAt).getTime(); freshness = Number.isFinite(age) ? (age < 7 * 86400000 ? 'Recent (within 7 days)' : 'Older than 7 days') : 'Date unavailable'; }
  else if (publishedText && /^(just now|yesterday|\d+\s*(s|m|h|d))$/i.test(publishedText)) freshness = /^(just now|\d+\s*(s|m|h))$/i.test(publishedText) ? 'Very recent' : 'Within the last 2 days';
  return {
    author: normalize((authorNode?.textContent || '').replace(/\s+follow\b.*$/i, '')) || null,
    published_at: publishedAt,
    published_text: publishedText,
    freshness,
    visible_links: [...new Set(links)].slice(0, 8),
    extraction_scope: 'Detected post caption/text and any explicitly selected readable image or video text',
  };
}
function findBestVideo(post) {
  const videos = [...post.querySelectorAll('video')];
  return videos.sort((a, b) => {
    const ar = (b.clientWidth * b.clientHeight) - (a.clientWidth * a.clientHeight);
    return ar || Number(Boolean(b.currentSrc)) - Number(Boolean(a.currentSrc));
  })[0] || null;
}
function collectPostMedia(post) {
  const images = [...post.querySelectorAll('img[src], img[currentSrc]')]
    .map((node) => node.currentSrc || node.src).filter((url) => /^https?:/i.test(url));
  const activeVideo = findBestVideo(post); const video = activeVideo?.currentSrc || activeVideo?.src ? activeVideo : post.querySelector('video source[src]');
  const videoUrl = video?.currentSrc || video?.src || video?.getAttribute?.('src') || null;
  return { image_urls: [...new Set(images)].slice(0, 4), video_url: /^(https?:|blob:)/i.test(videoUrl || '') ? videoUrl : null, has_video: Boolean(activeVideo || post.querySelector('[data-video-id], [aria-label*="video" i]')) };
}
function setMessage(container, text, tone = 'muted') { container.textContent = text; container.dataset.tone = tone; }
function appendLookupChoice(container) {
  const label = document.createElement('label');
  label.style.cssText = 'display:flex;gap:9px;align-items:flex-start;margin:12px 0;padding:10px;border:1px solid #99bdb5;border-radius:8px;background:#ecfdf5;color:#134e4a;font:600 13px/1.4 Arial;';
  const checkbox = document.createElement('input'); checkbox.type = 'checkbox'; checkbox.checked = retrievalEnabled; checkbox.style.cssText = 'width:17px;height:17px;margin-top:1px;accent-color:#0f766e;flex:none;';
  const text = document.createElement('span'); text.textContent = tr('Search approved news sources and published fact-check reviews for this analysis.', 'Maghanap sa mga aprubadong news source at nailathalang fact-check para sa pagsusuring ito.');
  checkbox.addEventListener('change', () => { retrievalEnabled = checkbox.checked; chrome.storage.local.set({ suriphRetrieveSources: retrievalEnabled }); });
  label.append(checkbox, text); container.appendChild(label);
}
async function captureVisibleVideo(post) {
  const video = findBestVideo(post);
  if (!video || typeof video.captureStream !== 'function') throw new Error('This browser did not expose a capturable video stream. Use the video file upload instead.');
  if (!Number.isFinite(video.duration) || video.duration <= 0) throw new Error('The video duration is not ready yet. Play it briefly, then try again.');
  const expectedDuration = video.duration; video.loop = false; video.autoplay = false;
  const stream = video.captureStream();
  const recorder = new MediaRecorder(stream, { mimeType: 'video/webm;codecs=vp8,opus' });
  const chunks = []; recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
  const stopped = new Promise((resolve, reject) => { recorder.onerror = () => reject(new Error('The browser could not capture this video.')); recorder.onstop = () => resolve(new Blob(chunks, { type: 'video/webm' })); });
  video.currentTime = 0; await video.play(); recorder.start(1000);
  await new Promise((resolve) => { let done = false; let highestTime = 0; const finish = () => { if (done) return; done = true; clearInterval(poll); clearTimeout(limit); video.removeEventListener('ended', finish); resolve(); }; const poll = setInterval(() => { const current = video.currentTime; if (current > highestTime) highestTime = current; const restarted = highestTime > expectedDuration * 0.75 && current < 1; if (video.ended || current >= expectedDuration - 0.25 || restarted) finish(); else if (video.paused) video.play().catch(() => {}); }, 200); const limit = setTimeout(finish, Math.min(Math.max(expectedDuration * 1000 + 1000, 5000), 3 * 60 * 1000)); video.addEventListener('ended', finish, { once: true }); });
  if (recorder.state !== 'inactive') recorder.stop(); const blob = await stopped; try { video.pause(); video.loop = false; video.autoplay = false; video.currentTime = Math.max(0, expectedDuration - 0.1); } catch (_) {} return blob;
}
async function obtainVideoBlob(post, url) {
  if (url) {
    try { const response = await fetch(url, { credentials: 'include' }); if (response.ok) { const blob = await response.blob(); if (blob.size) return blob; } } catch (_) {}
  }
  return captureVisibleVideo(post);
}
function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer); let binary = ''; const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) binary += String.fromCharCode(...bytes.subarray(index, index + chunkSize));
  return btoa(binary);
}
function renderRichResult(container, result) {
  const tl = interfaceLanguage === 'tl';
  const label = result.internal_label === 'Misleading' ? 'Potentially Misleading' : 'No Misleading Information Detected';
  const selectedScore = Number.isFinite(result.displayed_class_score) ? Number(result.displayed_class_score) : Number(result.confidence);
  const pct = (value) => value > .99995 && value < 1 ? '>99.99' : value > 0 && value < .00005 ? '<0.01' : (value * 100).toFixed(2);
  const addText = (tag, text, css = '') => { const node = document.createElement(tag); node.textContent = text; if (css) node.style.cssText = css; container.appendChild(node); return node; };
  const safeUrl = (value) => { try { const parsed = new URL(value); return ['https:', 'http:'].includes(parsed.protocol) ? parsed.href : null; } catch (_) { return null; } };
  container.replaceChildren(); container.style.color = '#0f172a'; container.style.marginTop = '8px';

  const language = document.createElement('div'); language.setAttribute('role', 'group'); language.setAttribute('aria-label', 'Interface language'); language.style.cssText = 'display:flex;gap:4px;justify-content:flex-end;margin:0 40px 10px 0;';
  [['English', 'en'], ['Tagalog', 'tl']].forEach(([name, value]) => { const choice = document.createElement('button'); choice.type = 'button'; choice.textContent = name; choice.setAttribute('aria-pressed', String(interfaceLanguage === value)); choice.style.cssText = `padding:6px 10px;border:1px solid #0f766e;border-radius:7px;background:${interfaceLanguage === value ? '#0f766e' : '#fff'};color:${interfaceLanguage === value ? '#fff' : '#0f766e'};font-weight:700;cursor:pointer;`; choice.addEventListener('click', () => { interfaceLanguage = value; chrome.storage.local.set({ suriphLanguage: value }); renderRichResult(container, result); }); language.appendChild(choice); });
  container.appendChild(language);

  addText('div', 'SuriPH', 'margin-bottom:8px;color:#0f766e;font-size:20px;font-weight:800;');
  const checked = document.createElement('section'); checked.style.cssText = 'padding:12px;border:1px solid #99bdb5;border-left:4px solid #0f766e;border-radius:10px;background:#fff;';
  const checkedTitle = document.createElement('b'); checkedTitle.textContent = tl ? 'Sinuring teksto' : 'Analyzed text';
  const checkedText = document.createElement('p'); checkedText.textContent = result.analyzed_text || ''; checkedText.style.cssText = 'max-height:150px;overflow:auto;margin:7px 0 0;white-space:pre-wrap;overflow-wrap:anywhere;'; checked.append(checkedTitle, checkedText); container.appendChild(checked);

  const context = result.context_explanation || {};
  const contextBox = document.createElement('section'); contextBox.className = 'context-box';
  const contextTitle = document.createElement('b'); contextTitle.textContent = tl ? 'Konteksto ng sinuring content' : 'Context of the analyzed content'; contextBox.appendChild(contextTitle);
  const contextRows = [
    [tl ? 'May-akda/source' : 'Author/source', context.author],
    [tl ? 'Oras o petsa ng post' : 'Post time/date', context.timing],
    [tl ? 'Sinuring bahagi' : 'Material checked', context.checked_material],
  ];
  for (const [name, value] of contextRows) if (value) { const row = document.createElement('p'); row.textContent = `${name}: ${value}`; row.style.cssText = 'margin:5px 0;'; contextBox.appendChild(row); }
  const contextLimit = document.createElement('p'); contextLimit.textContent = tl ? 'Hindi hiwalay na napatunayan ng SuriPH ang may-akda, petsa, o bawat pahayag. Suriin ang orihinal na post at mga link sa ibaba.' : 'SuriPH has not independently verified the author, date, or each statement. Review the original post and the links below.'; contextLimit.style.cssText = 'margin:7px 0 0;color:#475569;font-size:12px;'; contextBox.appendChild(contextLimit); container.appendChild(contextBox);

  const heading = addText('strong', label, `display:block;margin:2px 0 4px;padding:14px 16px;border-radius:10px;background:${result.internal_label === 'Misleading' ? '#fef3c7' : '#d1fae5'};color:#143c35;font-size:18px;text-align:center;`);
  heading.setAttribute('role', 'status');
  addText('p', `${pct(selectedScore)}% ${tl ? 'score para sa prediction na ito' : 'score for this prediction'}`, 'margin:4px 0;font-size:18px;font-weight:800;');
  addText('p', tl ? 'Ang score na ito ay para sa hula ng modelo. Hindi nito pinatutunayang totoo o mali ang pahayag.' : 'This score describes the model’s prediction. It does not confirm whether the claim is true.', 'margin:0 0 8px;');
  addText('p', result.internal_label === 'Misleading' ? (tl ? 'Prediction ito ng modelo at hindi beripikadong hatol sa katotohanan. Suriin ang source, petsa, at buong konteksto.' : 'This is a model prediction, not a verified factual verdict. Check the source, date and full context.') : (tl ? 'Ang “No Misleading Information Detected” ay hindi patunay na totoo ang pahayag. Suriin ang source, petsa, at buong konteksto.' : '“No Misleading Information Detected” does not confirm that the claim is true. Check the source, date and full context.'), 'padding:10px 12px;border-left:4px solid #d59b25;border-radius:6px;background:#fffbeb;color:#713f12;');

  const scoreDetails = document.createElement('details'); const scoreSummary = document.createElement('summary'); scoreSummary.textContent = tl ? 'Detalye ng score' : 'Score details'; const scoreText = document.createElement('p'); scoreText.textContent = `P(Misleading): ${pct(Number(result.model_score))}% · ${tl ? 'Threshold ng desisyon' : 'Decision threshold'}: ${pct(Number(result.decision_threshold))}%`; scoreDetails.append(scoreSummary, scoreText); container.appendChild(scoreDetails);

  const signals = document.createElement('details'); const signalsTitle = document.createElement('summary'); signalsTitle.textContent = tl ? 'Mga katangian ng teksto' : 'Text signals'; signals.appendChild(signalsTitle);
  const signalNote = document.createElement('p'); signalNote.textContent = tl ? 'Ito ang pitong hindi na-scale na sukat mula sa hybrid pipeline. Mga katangian ito ng teksto, hindi patunay ng misinformation o paliwanag sa sanhi ng prediction.' : 'These are the seven unscaled measurements from the hybrid pipeline. They are text characteristics, not proof of misinformation or explanations of what caused the prediction.'; signals.appendChild(signalNote);
  for (const item of result.linguistic_indicators || []) { const row = document.createElement('p'); const name = tl ? item.display_name_tagalog : item.display_name; const definition = tl ? item.definition_tagalog : item.definition; row.textContent = `${name || item.name}: ${Number(item.value).toFixed(4)} ratio. ${definition || ''}`; signals.appendChild(row); }
  container.appendChild(signals);

  if (result.extraction?.transcript_text || result.extraction?.frame_ocr_text) { const extraction = document.createElement('details'); const title = document.createElement('summary'); title.textContent = tl ? 'Tekstong kinuha sa video' : 'Video text extraction'; extraction.appendChild(title); if (result.extraction.transcript_text) { const speech = document.createElement('p'); speech.textContent = `${tl ? 'Salita mula sa audio' : 'Speech transcript'}: ${result.extraction.transcript_text}`; extraction.appendChild(speech); } if (result.extraction.frame_ocr_text) { const frames = document.createElement('p'); frames.textContent = `${tl ? 'Teksto sa mga frame' : 'On-screen frame text'}: ${result.extraction.frame_ocr_text}`; extraction.appendChild(frames); } container.appendChild(extraction); }

  const sourceBox = (title, note, items, status) => { const box = document.createElement('section'); box.className = 'sources'; box.style.cssText = 'padding:12px;border:1px solid #bae6fd;border-radius:10px;background:#f0f9ff;color:#334155;'; const head = document.createElement('b'); head.textContent = title; const help = document.createElement('span'); help.textContent = note; box.append(head, help); if (items.length) items.slice(0, 3).forEach((item) => { const href = safeUrl(item.url); if (!href) return; const article = document.createElement('article'); article.style.cssText = 'padding-top:8px;border-top:1px solid #bae6fd;'; const link = document.createElement('a'); link.href = href; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.textContent = item.title || item.claim || href; article.appendChild(link); const meta = [item.source || item.publisher, item.date || item.review_date, item.rating ? `${tl ? 'Rating' : 'Published rating'}: ${item.rating}` : ''].filter(Boolean).join(' · '); if (meta) { const details = document.createElement('small'); details.textContent = meta; article.appendChild(details); } const summary = item.snippet || item.claim; if (summary && summary !== item.title) { const snippet = document.createElement('span'); snippet.textContent = summary; snippet.style.cssText = 'margin-top:3px;'; article.appendChild(snippet); } box.appendChild(article); }); else { const empty = document.createElement('span'); empty.textContent = status; box.appendChild(empty); } container.appendChild(box); };
  const sourceStatus = result.retrieval_status === 'not_requested' ? (tl ? 'Hindi naka-on ang source lookup para sa request na ito. I-check ang source lookup bago suriin muli.' : 'Source lookup was off for this request. Turn it on before analyzing again.') : result.retrieval_status === 'no_results' ? (tl ? 'Walang tumugmang link. Hindi nito pinatutunayan ang prediction.' : 'No matching links were returned. Missing links do not validate the prediction.') : (tl ? 'Hindi magamit ang paghahanap. Hindi nagbago ang prediction.' : 'Related-source lookup is unavailable. The prediction is unchanged.');
  sourceBox(tl ? 'Mga kaugnay na source mula sa aprubadong publisher' : 'Related sources from approved publishers', tl ? 'Kaugnay na babasahin lamang; hindi awtomatikong ebidensya.' : 'Related reading only; not automatically supporting or debunking evidence.', result.related_sources || [], sourceStatus);
  const factStatus = result.fact_check_status === 'not_requested' ? (tl ? 'Hindi hiniling ang fact-check lookup.' : 'Published fact-check lookup was not requested.') : result.fact_check_status === 'no_results' ? (tl ? 'Walang tumugmang nailathalang review.' : 'No matching published review was returned.') : (tl ? 'Hindi magamit ang fact-check lookup. Hindi nagbago ang prediction.' : 'Published fact-check lookup is unavailable. The prediction is unchanged.');
  sourceBox(tl ? 'Mga nailathalang fact-check' : 'Published fact-check reviews', tl ? 'Hiwalay ang mga ito sa prediction at hindi nila ito binabago.' : 'These are independent from the prediction and do not change it.', result.fact_check_matches || [], factStatus);
  if (result.media_status === 'unavailable') addText('p', `${tl ? 'Hindi magamit ang media' : 'Media unavailable'}: ${result.media_error || ''}`, 'color:#991b1b;');
  addText('p', tl ? 'Research prototype. Maaaring magkamali ang prediction.' : 'Research prototype. Predictions can be wrong.', 'font-size:12px;color:#64748b;');
  container.dataset.tone = result.internal_label === 'Misleading' ? 'warn' : 'safe';
}
function renderMediaChooser(post, button, message, result, media) {
  result.replaceChildren();
  const title = document.createElement('strong'); title.textContent = tr('What would you like SuriPH to check?', 'Ano ang gusto mong suriin ng SuriPH?'); title.style.cssText = 'display:block;font-size:18px;margin-bottom:8px;color:#0f172a'; result.appendChild(title);
  const note = document.createElement('span'); note.textContent = tr('This post contains media. Choose the media itself or the caption.', 'May media ang post na ito. Piliin ang media o ang caption.'); result.appendChild(note);
  appendLookupChoice(result);
  const choices = document.createElement('div'); choices.style.cssText = 'display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:8px;';
  const addChoice = (label, mode) => { const choice = document.createElement('button'); choice.type = 'button'; choice.textContent = label; choice.style.cssText = 'height:44px;border:0;border-radius:10px;background:#0ea5e9;color:#fff;font:700 14px Arial;cursor:pointer;'; choice.addEventListener('click', () => { result.replaceChildren(); button.dataset.choicePending = 'false'; analyzePost(post, button, message, result, mode); }); choices.appendChild(choice); };
  if (media.has_video) addChoice(tr('Check this video', 'Suriin ang video'), 'video');
  if (media.image_urls?.length) addChoice(tr('Check this image', 'Suriin ang image'), 'image');
  addChoice(tr('Check caption/text', 'Suriin ang caption/teksto'), 'text'); result.appendChild(choices);
}
function analyzePost(post, button, message, result, mediaChoice = 'auto') {
  const host = button.getRootNode().host;
  if (activeResultHost && activeResultHost !== host) activeResultHost.remove();
  activeResultHost = host;
  // Escape Facebook's transformed/stacked post containers so the result is truly clickable.
  document.body.appendChild(host);
  host.style.cssText = 'position:fixed;inset:0;z-index:2147483646;display:flex;align-items:center;justify-content:center;background:rgba(2,6,23,.72);pointer-events:auto;';
  const expandedWrap = button.closest('.wrap'); expandedWrap?.classList.add('expanded'); if (expandedWrap) { expandedWrap.style.position = 'relative'; expandedWrap.style.display = 'flex'; expandedWrap.style.flexDirection = 'column'; expandedWrap.style.setProperty('background', '#ffffff', 'important'); expandedWrap.style.color = '#0f172a'; }
  button.style.order = '3'; button.style.marginTop = '14px'; message.style.order = '1'; message.style.color = '#334155'; result.style.order = '2';
  if (mediaChoice === 'auto' && button.dataset.choicePending !== 'false') { const detectedMedia = collectPostMedia(post); if (detectedMedia.has_video || detectedMedia.image_urls?.length) { button.dataset.choicePending = 'true'; setMessage(message, tr('Choose what you want SuriPH to check.', 'Piliin kung ano ang susuriin ng SuriPH.'), 'muted'); renderMediaChooser(post, button, message, result, detectedMedia); return; } }
  result.replaceChildren();
  button.disabled = true; button.textContent = tr('Checking…', 'Sinusuri…'); setMessage(message, tr('SuriPH is checking this post and its available context…', 'Sinusuri ng SuriPH ang post at available na konteksto…'), 'loading');
  const progress = [tr('SuriPH is reading the post context...', 'Binabasa ng SuriPH ang konteksto ng post...'), mediaChoice === 'video' ? tr('SuriPH is processing video frames and speech...', 'Pinoproseso ng SuriPH ang mga frame at salita sa video...') : mediaChoice === 'image' ? tr('SuriPH is reading the image and its text...', 'Binabasa ng SuriPH ang image at teksto nito...') : tr('SuriPH is checking the post and its context...', 'Sinusuri ng SuriPH ang post at konteksto nito...')];
  let progressIndex = 0; const startedAt = Date.now(); setMessage(message, progress[progressIndex], 'loading');
  let timedOut = false; const progressTimer = setInterval(() => { progressIndex = (progressIndex + 1) % progress.length; const elapsed = Math.round((Date.now() - startedAt) / 1000); setMessage(message, `${progress[progressIndex]} (${elapsed}s)`, 'loading'); }, 2200);
  const hardTimeout = setTimeout(() => { timedOut = true; clearInterval(progressTimer); button.disabled = false; button.textContent = tr('Check again', 'Suriin muli'); setMessage(message, tr('Video processing took too long and was stopped. Try a shorter video or upload the file through the popup.', 'Masyadong matagal ang pagproseso ng video. Subukan ang mas maikling video o i-upload ang file sa popup.'), 'error'); }, 300000);
  const text = collectPostText(post);
  const media = collectPostMedia(post);
  const selectedMedia = mediaChoice === 'video' ? { video_url: media.video_url, has_video: media.has_video } : mediaChoice === 'image' ? { image_urls: media.image_urls } : {};
  if (!text && (mediaChoice === 'text' || (mediaChoice === 'auto' && !media.has_video && !media.image_urls?.length))) { clearTimeout(hardTimeout); clearInterval(progressTimer); button.disabled = false; button.textContent = tr('Check with SuriPH', 'Suriin gamit ang SuriPH'); setMessage(message, tr('No readable Facebook post caption or text was found.', 'Walang nakitang mababasang caption o teksto ng Facebook post.'), 'error'); return; }
  if (text && (mediaChoice === 'text' || (mediaChoice === 'auto' && !media.has_video && !media.image_urls?.length)) && button.dataset.previewConfirmed !== 'true') {
    clearTimeout(hardTimeout); clearInterval(progressTimer); button.disabled = false; button.textContent = tr('Check with SuriPH', 'Suriin gamit ang SuriPH'); setMessage(message, tr('Review the exact text before it is sent to the model.', 'Basahin muna ang eksaktong tekstong ipapadala sa modelo.'));
    const preview = document.createElement('section'); preview.style.cssText = 'padding:12px;border:1px solid #99bdb5;border-radius:10px;background:#f8fafc;';
    const title = document.createElement('b'); title.textContent = interfaceLanguage === 'tl' ? 'Tekstong susuriin' : 'Text to analyze';
    const body = document.createElement('p'); body.textContent = text; body.style.cssText = 'max-height:180px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;';
    const confirm = document.createElement('button'); confirm.type = 'button'; confirm.textContent = interfaceLanguage === 'tl' ? 'Suriin ang tekstong ito' : 'Analyze this text'; confirm.style.cssText = 'width:100%;padding:10px;border:0;border-radius:8px;background:#0f766e;color:white;font-weight:700;cursor:pointer;';
    confirm.addEventListener('click', () => { button.dataset.previewConfirmed = 'true'; result.replaceChildren(); analyzePost(post, button, message, result, mediaChoice); });
    preview.append(title, body); appendLookupChoice(preview); preview.appendChild(confirm); result.appendChild(preview); return;
  }
  if (mediaChoice === 'video' && media.has_video) {
    setMessage(message, media.video_url ? tr('SuriPH is retrieving the loaded video content...', 'Kinukuha ng SuriPH ang naka-load na video...') : tr('SuriPH is capturing the video playback...', 'Kinukuha ng SuriPH ang video playback...'), 'loading');
    obtainVideoBlob(post, media.video_url).then((blob) => { if (timedOut) return null; clearInterval(progressTimer); const playedVideo = findBestVideo(post); try { playedVideo?.pause(); if (playedVideo) { playedVideo.loop = false; playedVideo.autoplay = false; if (Number.isFinite(playedVideo.duration)) playedVideo.currentTime = Math.max(0, playedVideo.duration - 0.1); } } catch (_) {} setMessage(message, tr('Video captured. SuriPH is now extracting speech and on-screen text...', 'Nakuha ang video. Kinukuha na ng SuriPH ang salita at on-screen text...'), 'loading'); return blob.arrayBuffer(); }).then((arrayBuffer) => { if (!arrayBuffer || timedOut) return; const videoBase64 = arrayBufferToBase64(arrayBuffer); chrome.runtime.sendMessage({ type: 'SURIPH_ANALYZE_CAPTURE', videoBase64, payload: { text, page_url: location.href, page_title: document.title, context: collectPostContext(post), retrieve_sources: retrievalEnabled } }, (response) => {
      if (timedOut) return; clearInterval(progressTimer); clearTimeout(hardTimeout); const runtimeError = chrome.runtime.lastError; button.disabled = false; button.textContent = tr('Check again', 'Suriin muli'); if (runtimeError || !response?.ok) { setMessage(message, localizedError(response?.error || 'The in-page video could not be processed.'), 'error'); return; } setMessage(message, '');  button.dataset.recheck = 'true'; renderRichResult(result, response.result);
    }); }).catch((error) => { if (timedOut) return; clearInterval(progressTimer); clearTimeout(hardTimeout); button.disabled = false; button.textContent = tr('Check again', 'Suriin muli'); setMessage(message, localizedError(error.message), 'error'); });
    return;
  }
  chrome.runtime.sendMessage({ type: 'SURIPH_ANALYZE_TEXT', payload: { text, page_url: location.href, page_title: document.title, context: collectPostContext(post), media: selectedMedia, retrieve_sources: retrievalEnabled } }, (response) => {
    clearInterval(progressTimer);
    if (timedOut) return; clearTimeout(hardTimeout); const runtimeError = chrome.runtime.lastError; button.disabled = false; button.textContent = tr('Check again', 'Suriin muli');
    if (runtimeError || !response?.ok) { setMessage(message, localizedError(response?.error || 'SuriPH backend is unavailable.'), 'error'); return; }
    setMessage(message, '');

    button.dataset.recheck = 'true';
    renderRichResult(result, response.result);
  });
}
function injectControl(post) {
  if (post.closest('#suriph-control-host') || post.querySelector(`[${CONTROL_ATTRIBUTE}]`)) return;
  post.setAttribute(CONTROL_ATTRIBUTE, 'true');
  if (window.getComputedStyle(post).position === 'static') post.style.position = 'relative';
  const host = document.createElement('div'); host.id = 'suriph-control-host'; host.setAttribute('aria-label', 'SuriPH post screening control'); host.style.cssText = 'position:absolute;right:10px;top:10px;z-index:2147483646;';
  const shadow = host.attachShadow({ mode: 'open' }); const style = document.createElement('style');
  style.textContent = ':host{all:initial;display:block;pointer-events:auto;font-family:Arial,Helvetica,sans-serif}.wrap{width:34px;display:flex;flex-direction:column;gap:8px;pointer-events:auto}.wrap.expanded{position:relative;display:flex;flex-direction:column;width:560px;max-width:calc(100vw - 32px);max-height:calc(100vh - 64px);overflow:auto;padding:20px;border:1px solid #cbd5e1;border-radius:18px;background:#fff!important;color:#0f172a;box-shadow:0 24px 80px rgba(15,23,42,.4);pointer-events:auto}.wrap.expanded:before{content:none!important}.action{box-sizing:border-box;width:34px;height:34px;margin:0;border:0;border-radius:999px;background:#10b981;color:#052e24;font:700 15px Arial;cursor:pointer;box-shadow:0 4px 14px rgba(16,185,129,.35);pointer-events:auto}.action:hover{background:#34d399}.expanded .action{order:3;width:100%;height:46px;margin-top:16px;border-radius:10px;font-size:16px}.action:disabled{opacity:.65;cursor:wait}.close{display:none;position:absolute;top:12px;right:12px;width:34px;height:34px;border:0;border-radius:9px;background:#334155;color:#fff;font:700 20px Arial;line-height:34px;cursor:pointer;z-index:3;pointer-events:auto}.expanded .close{display:block;font-size:0}.expanded .close:before{content:"X";font-size:18px}.close:hover{background:#1e293b}.message{order:1;color:#334155;font:14px/1.5 Arial;white-space:normal}.message:empty{display:none}.message[data-tone=loading]{display:flex;align-items:center;gap:10px;padding:20px 4px;justify-content:center}.message[data-tone=loading]:before{content:"";width:20px;height:20px;border:3px solid #cbd5e1;border-top-color:#10b981;border-radius:50%;animation:spin .8s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}.message[data-tone=error]{color:#b91c1c}.result{order:2;display:flex;flex-direction:column;gap:10px;color:#0f172a;font:14px/1.5 Arial}.result a{color:#0369a1;text-decoration:underline;overflow-wrap:anywhere}.result details{padding:10px 12px;border:1px solid #dbe4ee;border-radius:10px;background:#f8fafc}.result summary{cursor:pointer;color:#334155;font-weight:700}.result details div{margin-top:8px;white-space:pre-wrap;overflow-wrap:anywhere}.result span{display:block}.result small{color:#64748b}.result .context-box{padding:12px;border:1px solid #dbe4ee;border-radius:10px;background:#f8fafc}.result .sources{display:flex;flex-direction:column;gap:4px}.result .disclaimer{margin-top:4px}.wrap.expanded::-webkit-scrollbar{width:10px}.wrap.expanded::-webkit-scrollbar-thumb{background:#94a3b8;border-radius:99px;border:3px solid #fff}';
  const wrap = document.createElement('div'); wrap.className = 'wrap'; const button = document.createElement('button'); button.className = 'action'; button.type = 'button'; button.textContent = 'S'; button.dataset.recheck = 'false'; button.title = tr('Check with SuriPH', 'Suriin gamit ang SuriPH'); const close = document.createElement('button'); close.type = 'button'; close.className = 'close'; close.textContent = '×'; close.title = tr('Close result', 'Isara ang resulta'); const message = document.createElement('div'); message.className = 'message'; const result = document.createElement('div'); result.className = 'message result'; close.addEventListener('click', (event) => { event.preventDefault(); event.stopPropagation(); wrap.classList.remove('expanded'); wrap.style.position = ''; wrap.style.display = ''; wrap.style.flexDirection = ''; wrap.style.removeProperty('background'); wrap.style.color = ''; button.style.order = ''; button.style.marginTop = ''; message.style.order = ''; message.style.color = ''; result.style.order = ''; message.replaceChildren(); result.replaceChildren(); button.disabled = false; button.textContent = 'S'; button.dataset.recheck = 'false'; delete button.dataset.previewConfirmed; post.appendChild(host); host.style.cssText = 'position:absolute;right:10px;top:10px;z-index:2147483646;'; if (activeResultHost === host) activeResultHost = null; }); button.addEventListener('click', () => analyzePost(post, button, message, result)); wrap.append(close, button, message, result); shadow.append(style, wrap); post.appendChild(host);
}
function scanForControls() { if (extensionEnabled) for (const post of findPosts()) injectControl(post); }
function removeControls() { document.querySelectorAll('#suriph-control-host').forEach((host) => host.remove()); document.querySelectorAll(`[${CONTROL_ATTRIBUTE}]`).forEach((post) => post.removeAttribute(CONTROL_ATTRIBUTE)); }
chrome.storage.local.get({ suriphEnabled: true, suriphRetrieveSources: false, suriphLanguage: 'en' }, (settings) => {
  extensionEnabled = settings.suriphEnabled !== false;
  retrievalEnabled = settings.suriphRetrieveSources === true;
  interfaceLanguage = settings.suriphLanguage === 'tl' ? 'tl' : 'en';
  scanForControls();
});
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.suriphRetrieveSources) retrievalEnabled = changes.suriphRetrieveSources.newValue === true;
  if (area === 'local' && changes.suriphLanguage) interfaceLanguage = changes.suriphLanguage.newValue === 'tl' ? 'tl' : 'en';
});
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === 'SURIPH_EXTRACT') {
    if (message.mode === 'selection') {
      const text = normalize(window.getSelection()?.toString());
      sendResponse(text ? { ok: true, text, mode: 'selection' } : { ok: false, error: tr('Select readable text on the page first.', 'Pumili muna ng mababasang teksto sa Facebook page.') });
      return false;
    }
    if (message.mode === 'post') {
      const post = postForSelection() || postNearestViewport();
      const text = post ? collectPostText(post) : '';
      sendResponse(text ? { ok: true, text, mode: 'post' } : { ok: false, error: tr('No readable Facebook post or caption is visible.', 'Walang nakikitang mababasang Facebook post o caption.') });
      return false;
    }
    sendResponse({ ok: false, error: 'Unsupported extraction mode.' });
    return false;
  }
  if (message?.type === 'SURIPH_SET_ENABLED') {
    extensionEnabled = Boolean(message.enabled); chrome.storage.local.set({ suriphEnabled: extensionEnabled });
    if (!extensionEnabled) removeControls(); else scanForControls();
    sendResponse({ ok: true });
    return false;
  }
  return false;
});
new MutationObserver(scanForControls).observe(document.documentElement, { childList: true, subtree: true });
