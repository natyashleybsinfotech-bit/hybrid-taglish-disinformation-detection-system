// Inject controls proactively; page content is read only after a user click.
const POST_SELECTORS = ['article', '[data-testid="tweetText"]', '[role="article"]', 'ytd-watch-metadata'];
const CONTROL_ATTRIBUTE = 'data-suriph-control';
const MAX_TEXT_LENGTH = 20_000;
let extensionEnabled = true;
let activeResultHost = null;
const cachedPostResults = new WeakMap();

function rootsFrom(root = document) {
  const roots = [root];
  for (const element of root.querySelectorAll('*')) {
    if (element.id === 'suriph-control-host') continue;
    if (element.shadowRoot) roots.push(...rootsFrom(element.shadowRoot));
  }
  return roots;
}
function normalize(value) { return (value || '').replace(/\s+/g, ' ').trim(); }
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
  const parts = [post.innerText || post.textContent || ''];
  for (const root of rootsFrom(post)) if (root !== post && root.host?.id !== 'suriph-control-host') parts.push(root.innerText || root.textContent || '');
  return normalize([...new Set(parts.map(normalize).filter(Boolean))].join(' ')).slice(0, MAX_TEXT_LENGTH);
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
    extraction_scope: 'Post text, caption, visible surrounding context, and any readable image or video text',
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
  const label = result.public_label || 'Screening complete';
  const score = Number(result.temporary_score || 0) * 100;
  container.replaceChildren();
  container.style.color = '#0f172a';
  container.style.marginTop = '8px';

  const brand = document.createElement('div');
  brand.textContent = 'SuriPH';
  brand.style.cssText = 'margin-bottom:10px;color:#0f766e;font-size:20px;font-weight:800;letter-spacing:-.02em;';
  container.appendChild(brand);

  const heading = document.createElement('strong');
  heading.textContent = label;
  heading.style.cssText = 'display:block;margin:0 -2px 8px;padding:14px 16px;border-radius:10px;background:#10b981;color:#052e24;font-size:16px;text-align:center;';
  container.appendChild(heading);
  const scoreLine = document.createElement('span');
  scoreLine.textContent = `Confidence: ${score.toFixed(1)}%`;
  scoreLine.style.cssText = 'margin-bottom:4px;font-weight:700;';
  container.appendChild(scoreLine);
  if (result.decision_source === 'google_fact_check' && result.decision_basis) {
    const decisionBasis = document.createElement('p');
    decisionBasis.textContent = `Google fact-check evidence influenced this result: ${result.decision_basis}`;
    decisionBasis.style.cssText = 'margin:7px 0;padding:9px 10px;border:1px solid #c4b5fd;border-radius:8px;background:#f5f3ff;color:#4c1d95;font-size:12px;font-weight:600;line-height:1.45;';
    container.appendChild(decisionBasis);
  }

  const sources = document.createElement('div');
  sources.className = 'sources';
  sources.style.cssText = 'margin:4px 0 6px;padding:12px;border:1px solid #bae6fd;border-radius:10px;background:#f0f9ff;color:#334155;';
  const sourcesTitle = document.createElement('b');
  sourcesTitle.textContent = 'Related coverage from credible sources';
  sources.appendChild(sourcesTitle);
  if (result.related_sources?.length) {
    result.related_sources.slice(0, 3).forEach((item) => { const source = document.createElement('a'); source.href = item.url; source.target = '_blank'; source.rel = 'noreferrer'; source.textContent = item.title || item.url; sources.appendChild(source); });
  } else {
    const sourceStatus = document.createElement('span');
    sourceStatus.textContent = result.retrieval_status === 'unavailable'
      ? 'Credible-source lookup is temporarily unavailable. Try Check again.'
      : 'No matching credible article was found for this claim.';
    sources.appendChild(sourceStatus);
  }
  container.appendChild(sources);

  const factChecks = document.createElement('div');
  factChecks.style.cssText = 'margin:0 0 6px;padding:12px;border:1px solid #c4b5fd;border-radius:10px;background:#f5f3ff;color:#334155;display:grid;gap:7px;';
  const factCheckTitle = document.createElement('b');
  factCheckTitle.textContent = 'Published fact-checks from Google Fact Check Tools';
  factChecks.appendChild(factCheckTitle);
  if (result.fact_check_matches?.length) {
    result.fact_check_matches.forEach((match) => {
      const card = document.createElement('div');
      card.style.cssText = 'display:grid;gap:2px;padding-top:6px;border-top:1px solid #ddd6fe;';
      const rating = document.createElement('b');
      rating.textContent = `${match.publisher}: ${match.rating}`;
      const link = document.createElement('a');
      link.href = match.url; link.target = '_blank'; link.rel = 'noreferrer'; link.textContent = match.title || match.claim || 'Open fact-check article';
      card.append(rating, link); factChecks.appendChild(card);
    });
  } else {
    const status = document.createElement('span');
    status.textContent = result.fact_check_status === 'unavailable_not_configured'
      ? 'Google Fact Check is ready, but its API key has not been configured yet.'
      : result.fact_check_status === 'unavailable'
        ? 'Google Fact Check is temporarily unavailable.'
        : 'No previously fact-checked claim matched this post.';
    factChecks.appendChild(status);
  }
  container.appendChild(factChecks);

  if (result.context_explanation) {
    const context = result.context_explanation;
    const explanation = document.createElement('section');
    explanation.style.cssText = 'display:grid;gap:9px;margin-bottom:14px;padding:14px;border:1px solid #99f6e4;border-radius:12px;background:#f0fdfa;color:#134e4a;';
    const title = document.createElement('strong');
    title.textContent = 'Context overview';
    title.style.cssText = 'font-size:16px;color:#0f766e;';
    explanation.appendChild(title);
    const overviewLabel = document.createElement('b');
    overviewLabel.textContent = 'What the post is about';
    explanation.appendChild(overviewLabel);
    const overview = document.createElement('p');
    overview.textContent = context.overview || 'There was not enough readable content to produce a clear overview.';
    overview.style.cssText = 'margin:0;line-height:1.55;';
    explanation.appendChild(overview);

    if (context.separate_statements?.length) {
      const claimDetails = document.createElement('details');
      claimDetails.style.cssText = 'padding:9px 10px;border:1px solid #99f6e4;border-radius:8px;background:#fff;';
      const claimSummary = document.createElement('summary');
      claimSummary.textContent = `View ${context.separate_statements.length} separate statements`;
      claimSummary.style.cssText = 'cursor:pointer;font-weight:700;color:#0f766e;';
      claimDetails.appendChild(claimSummary);
      const list = document.createElement('div');
      list.style.cssText = 'display:grid;gap:7px;margin-top:8px;';
      context.separate_statements.forEach((claim) => {
        const item = document.createElement('div');
        item.style.cssText = 'display:grid;gap:3px;padding:7px 0;border-bottom:1px solid #e2e8f0;color:#334155;';
        const statement = document.createElement('span');
        statement.textContent = `${claim.number}. ${claim.statement}`;
        item.appendChild(statement);
        list.appendChild(item);
      });
      claimDetails.appendChild(list);
      explanation.appendChild(claimDetails);
    }

    const facts = document.createElement('div');
    facts.style.cssText = 'display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;padding-top:4px;';
    [['Source', context.author], ['Posted', context.timing], ['Recency', context.freshness]].forEach(([name, value]) => {
      if (!value) return;
      const fact = document.createElement('div');
      fact.style.cssText = 'padding:8px;border-radius:8px;background:#fff;color:#334155;';
      const factLabel = document.createElement('b');
      factLabel.textContent = `${name}: `;
      fact.append(factLabel, document.createTextNode(value));
      facts.appendChild(fact);
    });
    explanation.appendChild(facts);

    const addContextLine = (titleText, text) => {
      if (!text) return;
      const block = document.createElement('div');
      block.style.cssText = 'color:#334155;line-height:1.45;';
      const blockTitle = document.createElement('b');
      blockTitle.textContent = `${titleText}: `;
      block.append(blockTitle, document.createTextNode(text));
      explanation.appendChild(block);
    };
    addContextLine('Why timing matters', context.recency_explanation);
    addContextLine('How the statements were checked', context.assessment_scope);
    addContextLine('Content used', context.checked_material);
    addContextLine('Related coverage', context.related_coverage);
    container.appendChild(explanation);
  }

  if (result.media_status === 'unavailable') {
    const mediaNotice = document.createElement('span');
    mediaNotice.textContent = `Media: ${result.media_error || 'unavailable'} Text screening is still shown.`;
    mediaNotice.dataset.tone = 'error';
    container.appendChild(mediaNotice);
  }
  if (result.analyzed_text) {
    const details = document.createElement('details');
    const summary = document.createElement('summary');
    summary.textContent = 'View the content checked by SuriPH';
    const checkedText = document.createElement('div');
    checkedText.textContent = result.analyzed_text;
    details.append(summary, checkedText);
    container.appendChild(details);
  }
  container.dataset.tone = result.internal_label === 'Misleading' ? 'warn' : 'safe';
  if (result.disclaimer) {
    const disclaimer = document.createElement('div');
    disclaimer.textContent = result.disclaimer;
    disclaimer.style.cssText = 'margin-top:12px;padding:11px 12px;border:1px solid #f59e0b;border-left:4px solid #f59e0b;border-radius:8px;background:#fffbeb;color:#78350f;font-size:11px;line-height:1.45;font-weight:600;';
    container.appendChild(disclaimer);
  }
}

function renderResult(container, result) {
  const label = result.public_label || 'Screening complete';
  const score = Number(result.temporary_score || 0) * 100;
  container.replaceChildren();
  container.style.color = '#0f172a'; container.style.marginTop = '8px';
  const brand = document.createElement('div'); brand.textContent = 'SuriPH'; brand.style.cssText = 'margin-bottom:10px;color:#0f766e;font-size:20px;font-weight:800;letter-spacing:-.02em;'; container.appendChild(brand);
  const heading = document.createElement('strong'); heading.textContent = label; heading.style.cssText = 'display:block;margin:0 -2px 8px;padding:14px 16px;border-radius:10px;background:#10b981;color:#052e24;font-size:16px;text-align:center;'; container.appendChild(heading);
  const scoreLine = document.createElement('span'); scoreLine.textContent = `Confidence: ${score.toFixed(1)}%`; scoreLine.style.cssText = 'margin-bottom:4px;font-weight:700;'; container.appendChild(scoreLine);
  if (result.context_explanation) {
    const explanation = document.createElement('section'); explanation.style.cssText = 'display:grid;gap:8px;margin-bottom:14px;padding:14px;border:1px solid #99f6e4;border-radius:12px;background:#f0fdfa;color:#134e4a;';
    const title = document.createElement('strong'); title.textContent = 'Context overview'; title.style.cssText = 'font-size:16px;color:#0f766e;'; explanation.appendChild(title);
    const overviewLabel = document.createElement('b'); overviewLabel.textContent = 'What the post is about'; explanation.appendChild(overviewLabel);
    const overview = document.createElement('p'); overview.textContent = result.context_explanation.overview || 'There was not enough readable content to produce a clear overview.'; overview.style.cssText = 'margin:0;line-height:1.55;'; explanation.appendChild(overview);
    if (result.context_explanation.main_points?.length) { const pointsTitle = document.createElement('b'); pointsTitle.textContent = 'Separate claims identified'; explanation.appendChild(pointsTitle); const list = document.createElement('ul'); list.style.cssText = 'display:grid;gap:5px;margin:0;padding-left:20px;'; result.context_explanation.main_points.forEach((point) => { const item = document.createElement('li'); item.textContent = point; list.appendChild(item); }); explanation.appendChild(list); }
    const timing = document.createElement('small'); timing.textContent = `Source: ${result.context_explanation.author} | Posted: ${result.context_explanation.timing} | ${result.context_explanation.freshness}`; timing.style.cssText = 'color:#475569;line-height:1.45;'; explanation.appendChild(timing); container.appendChild(explanation);
  }
  if (result.context_explanation) {
    const explanationCard = container.querySelector('section'); const timingLine = explanationCard?.querySelector('small');
    if (timingLine) timingLine.textContent = `Source: ${result.context_explanation.author} | Posted: ${result.context_explanation.timing}`;
    const addContextLine = (text) => { if (!text || !explanationCard) return; const line = document.createElement('p'); line.textContent = text; line.style.cssText = 'margin:0;color:#334155;line-height:1.45;'; explanationCard.appendChild(line); };
    addContextLine(result.context_explanation.recency_explanation); addContextLine(result.context_explanation.assessment_scope); addContextLine(result.context_explanation.related_coverage);
  }
  if (!result.context_explanation && (result.page_title || result.page_url)) {
    const context = document.createElement('span'); context.textContent = `Context: ${result.page_title || result.page_url}`; context.title = result.page_url || '';
    container.appendChild(context);
  }
  if (!result.context_explanation && result.context && Object.values(result.context).some(Boolean)) {
    const contextBox = document.createElement('div'); contextBox.className = 'context-box'; contextBox.style.cssText = 'display:grid;gap:4px;margin-top:8px;padding:10px;border:1px solid #dbe4ee;border-radius:10px;background:#f7fafc;font-size:12px;color:#334155;';
    const contextTitle = document.createElement('span'); contextTitle.textContent = 'Post context'; contextBox.appendChild(contextTitle);
    [['Who posted it', result.context.author], ['When it was posted', result.context.published_text || result.context.published_at], ['How recent it is', result.context.freshness], ['What was checked', result.context.extraction_scope]].forEach(([name, value]) => {
      if (!value) return; const line = document.createElement('div'); const label = document.createElement('b'); label.textContent = `${name}: `; const val = document.createElement('span'); val.textContent = value; line.append(label, val); contextBox.appendChild(line);
    });
    if (result.context.visible_links?.length) { const links = document.createElement('div'); const label = document.createElement('b'); label.textContent = 'Post links: '; links.appendChild(label); links.append(document.createTextNode(`${result.context.visible_links.length} visible link(s)`)); contextBox.appendChild(links); }
    container.appendChild(contextBox);
  }
  if (result.retrieval_status === 'no_results') { const status = document.createElement('span'); status.textContent = 'No matching credible source was found for this claim.'; container.appendChild(status); }
  if (result.media_status === 'unavailable') { const mediaNotice = document.createElement('span'); mediaNotice.textContent = `Media: ${result.media_error || 'unavailable'} Text screening is still shown.`; mediaNotice.dataset.tone = 'error'; container.appendChild(mediaNotice); }
  if (result.analyzed_text) {
    const details = document.createElement('details'); const summary = document.createElement('summary'); summary.textContent = 'View the content checked by SuriPH';
    const text = document.createElement('div'); text.textContent = result.analyzed_text; details.append(summary, text); container.appendChild(details);
  }
  container.dataset.tone = result.internal_label === 'Misleading' ? 'warn' : 'safe';
  if (result.related_sources?.length) {
    const sources = document.createElement('div'); sources.className = 'sources'; sources.style.color = '#334155';
    const title = document.createElement('span'); title.textContent = 'CREDIBLE SOURCES'; sources.appendChild(title);
    result.related_sources.slice(0, 3).forEach((item) => { const source = document.createElement('a'); source.href = item.url; source.target = '_blank'; source.rel = 'noreferrer'; source.textContent = item.title || item.url; sources.appendChild(source); });
    container.appendChild(sources);
  }
  if (result.disclaimer) { const disclaimer = document.createElement('div'); disclaimer.textContent = result.disclaimer; disclaimer.style.cssText = 'margin-top:12px;padding:11px 12px;border:1px solid #f59e0b;border-left:4px solid #f59e0b;border-radius:8px;background:#fffbeb;color:#78350f;font-size:11px;line-height:1.45;font-weight:600;'; container.appendChild(disclaimer); }
}
function renderMediaChooser(post, button, message, result, media) {
  result.replaceChildren();
  const title = document.createElement('strong'); title.textContent = 'What would you like SuriPH to check?'; title.style.cssText = 'display:block;font-size:18px;margin-bottom:8px;color:#0f172a'; result.appendChild(title);
  const note = document.createElement('span'); note.textContent = 'This post contains media. Choose the media itself or the caption.'; result.appendChild(note);
  const choices = document.createElement('div'); choices.style.cssText = 'display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:8px;';
  const addChoice = (label, mode) => { const choice = document.createElement('button'); choice.type = 'button'; choice.textContent = label; choice.style.cssText = 'height:44px;border:0;border-radius:10px;background:#0ea5e9;color:#fff;font:700 14px Arial;cursor:pointer;'; choice.addEventListener('click', () => { result.replaceChildren(); button.dataset.choicePending = 'false'; analyzePost(post, button, message, result, mode); }); choices.appendChild(choice); };
  if (media.has_video) addChoice('Check this video', 'video');
  if (media.image_urls?.length) addChoice('Check this image', 'image');
  addChoice('Check caption/text', 'text'); result.appendChild(choices);
}
function analyzePost(post, button, message, result, mediaChoice = 'auto') {
  const cached = cachedPostResults.get(post);
  const forceRefresh = button.dataset.recheck === 'true' || mediaChoice !== 'auto';
  const host = button.getRootNode().host;
  if (activeResultHost && activeResultHost !== host) activeResultHost.remove();
  activeResultHost = host;
  // Escape Facebook's transformed/stacked post containers so the result is truly clickable.
  document.body.appendChild(host);
  host.style.cssText = 'position:fixed;inset:0;z-index:2147483646;display:flex;align-items:center;justify-content:center;background:rgba(2,6,23,.72);pointer-events:auto;';
  const expandedWrap = button.closest('.wrap'); expandedWrap?.classList.add('expanded'); if (expandedWrap) { expandedWrap.style.position = 'relative'; expandedWrap.style.display = 'flex'; expandedWrap.style.flexDirection = 'column'; expandedWrap.style.setProperty('background', '#ffffff', 'important'); expandedWrap.style.color = '#0f172a'; }
  button.style.order = '3'; button.style.marginTop = '14px'; message.style.order = '1'; message.style.color = '#334155'; result.style.order = '2';
  if (mediaChoice === 'auto' && button.dataset.choicePending !== 'false') { const detectedMedia = collectPostMedia(post); if (detectedMedia.has_video || detectedMedia.image_urls?.length) { button.dataset.choicePending = 'true'; setMessage(message, 'Choose what you want SuriPH to check.', 'muted'); renderMediaChooser(post, button, message, result, detectedMedia); return; } }
  if (cached && !forceRefresh) { button.textContent = 'Check again'; button.dataset.recheck = 'true'; setMessage(message, ''); renderRichResult(result, cached); return; }
  result.replaceChildren();
  button.disabled = true; button.textContent = 'Checking…'; setMessage(message, 'SuriPH is checking this post and its available context…', 'loading');
  const progress = ['SuriPH is reading the post context...', mediaChoice === 'video' ? 'SuriPH is processing video frames and speech...' : mediaChoice === 'image' ? 'SuriPH is reading the image and its text...' : 'SuriPH is checking the post and its context...'];
  let progressIndex = 0; const startedAt = Date.now(); setMessage(message, progress[progressIndex], 'loading');
  let timedOut = false; const progressTimer = setInterval(() => { progressIndex = (progressIndex + 1) % progress.length; const elapsed = Math.round((Date.now() - startedAt) / 1000); setMessage(message, `${progress[progressIndex]} (${elapsed}s elapsed)`, 'loading'); }, 2200);
  const hardTimeout = setTimeout(() => { timedOut = true; clearInterval(progressTimer); button.disabled = false; button.textContent = 'Check again'; setMessage(message, 'Video processing took too long and was stopped. Try a shorter video or upload the file through the popup.', 'error'); }, 300000);
  const text = collectPostText(post);
  const media = collectPostMedia(post);
  const selectedMedia = mediaChoice === 'video' ? { video_url: media.video_url, has_video: media.has_video } : mediaChoice === 'image' ? { image_urls: media.image_urls } : {};
  if (!text && mediaChoice === 'text') { clearInterval(progressTimer); button.disabled = false; button.textContent = 'Check with SuriPH'; setMessage(message, 'No readable post text found.', 'error'); return; }
  if (mediaChoice === 'video' && media.has_video) {
    setMessage(message, media.video_url ? 'SuriPH is retrieving the loaded video content...' : 'SuriPH is capturing the video playback...', 'loading');
    obtainVideoBlob(post, media.video_url).then((blob) => { if (timedOut) return null; clearInterval(progressTimer); const playedVideo = findBestVideo(post); try { playedVideo?.pause(); if (playedVideo) { playedVideo.loop = false; playedVideo.autoplay = false; if (Number.isFinite(playedVideo.duration)) playedVideo.currentTime = Math.max(0, playedVideo.duration - 0.1); } } catch (_) {} setMessage(message, 'Video captured. SuriPH is now extracting speech and on-screen text...', 'loading'); return blob.arrayBuffer(); }).then((arrayBuffer) => { if (!arrayBuffer || timedOut) return; const videoBase64 = arrayBufferToBase64(arrayBuffer); chrome.runtime.sendMessage({ type: 'SURIPH_ANALYZE_CAPTURE', videoBase64, payload: { text, page_url: location.href, page_title: document.title, context: collectPostContext(post) } }, (response) => {
      if (timedOut) return; clearInterval(progressTimer); clearTimeout(hardTimeout); const runtimeError = chrome.runtime.lastError; button.disabled = false; button.textContent = 'Check again'; if (runtimeError || !response?.ok) { setMessage(message, response?.error || 'The in-page video could not be processed.', 'error'); return; } setMessage(message, ''); cachedPostResults.set(post, response.result); button.dataset.recheck = 'true'; renderRichResult(result, response.result);
    }); }).catch((error) => { if (timedOut) return; clearInterval(progressTimer); clearTimeout(hardTimeout); button.disabled = false; button.textContent = 'Check again'; setMessage(message, error.message, 'error'); });
    return;
  }
  chrome.runtime.sendMessage({ type: 'SURIPH_ANALYZE_TEXT', payload: { text, page_url: location.href, page_title: document.title, context: collectPostContext(post), media: selectedMedia } }, (response) => {
    clearInterval(progressTimer);
    if (timedOut) return; clearTimeout(hardTimeout); const runtimeError = chrome.runtime.lastError; button.disabled = false; button.textContent = 'Check again';
    if (runtimeError || !response?.ok) { setMessage(message, response?.error || 'SuriPH backend is unavailable.', 'error'); return; }
    setMessage(message, '');
    cachedPostResults.set(post, response.result);
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
  const wrap = document.createElement('div'); wrap.className = 'wrap'; const button = document.createElement('button'); button.className = 'action'; button.type = 'button'; button.textContent = 'S'; button.dataset.recheck = 'false'; button.title = 'Check with SuriPH'; const close = document.createElement('button'); close.type = 'button'; close.className = 'close'; close.textContent = '×'; close.title = 'Close result'; const message = document.createElement('div'); message.className = 'message'; const result = document.createElement('div'); result.className = 'message result'; close.addEventListener('click', (event) => { event.preventDefault(); event.stopPropagation(); wrap.classList.remove('expanded'); wrap.style.position = ''; wrap.style.display = ''; wrap.style.flexDirection = ''; wrap.style.removeProperty('background'); wrap.style.color = ''; button.style.order = ''; button.style.marginTop = ''; message.style.order = ''; message.style.color = ''; result.style.order = ''; message.replaceChildren(); result.replaceChildren(); button.disabled = false; button.textContent = 'S'; button.dataset.recheck = 'false'; post.appendChild(host); host.style.cssText = 'position:absolute;right:10px;top:10px;z-index:2147483646;'; if (activeResultHost === host) activeResultHost = null; }); button.addEventListener('click', () => analyzePost(post, button, message, result)); wrap.append(close, button, message, result); shadow.append(style, wrap); post.appendChild(host);
}
function scanForControls() { if (extensionEnabled) for (const post of findPosts()) injectControl(post); }
function removeControls() { document.querySelectorAll('#suriph-control-host').forEach((host) => host.remove()); document.querySelectorAll(`[${CONTROL_ATTRIBUTE}]`).forEach((post) => post.removeAttribute(CONTROL_ATTRIBUTE)); }
chrome.storage.local.get({ suriphEnabled: true }, (settings) => { extensionEnabled = settings.suriphEnabled !== false; scanForControls(); });
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== 'SURIPH_SET_ENABLED') return false;
  extensionEnabled = Boolean(message.enabled); chrome.storage.local.set({ suriphEnabled: extensionEnabled });
  if (!extensionEnabled) removeControls(); else scanForControls();
  sendResponse({ ok: true }); return false;
});
new MutationObserver(scanForControls).observe(document.documentElement, { childList: true, subtree: true });
