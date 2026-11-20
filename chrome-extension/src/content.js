import modalCss from './modal.css?inline';
import { captionForScreening, matchesSubmittedPost, matchesVideoPreview, postResultCacheKey, resolveMediaChoice, usableVideoCaption } from './result_binding.js';
import { evidenceReaderNotice, incompleteVideoNotice, mergeRelatedSources, displayPostDate, displayPostRecency } from './result_updates.js';
import { captureVideoElement } from './video_capture.js';
import { isRecommendationSurface } from './post_eligibility.js';

// Inject controls proactively; page content is read only after a user click.
const POST_SELECTORS = [
  '[role="article"]', 'article',
  '[data-pagelet^="FeedUnit"]', '[data-pagelet*="FeedUnit_"]',
  '[data-testid="fbfeed_story"]',
];
const POST_TEXT_SELECTORS = [
  '[data-ad-comet-preview="message"]', '[data-ad-preview="message"]',
  '[data-ad-rendering-role="story_message"]', '[data-testid="post_message"]',
  '[data-testid="post-content"]',
];
const POST_AUTHOR_SELECTOR = '[data-ad-rendering-role="profile_name"], [data-ad-rendering-role="profile_name"] a[role="link"], [role="heading"] a[role="link"], h2 a[role="link"], h3 a[role="link"], [role="link"] strong, a[data-hovercard]';
const POST_TIMESTAMP_SELECTOR = 'time, [data-utime], a[href*="/posts/"], a[href*="/permalink/"], a[href*="story_fbid"], a[href*="permalink.php"], a[href*="story.php"], a[href*="/reel/"], a[href*="/watch/"], a[href*="/videos/"], a[href*="photo/?fbid="]';
const POST_SURFACE_SELECTOR = '[role="feed"], [role="main"], [data-pagelet*="Feed" i], [data-pagelet*="ProfileTimeline" i]';
const POST_ACTION_SELECTORS = [
  '[role="button"][aria-label^="Comment" i]', '[role="button"][aria-label^="Share" i]',
  '[role="button"][aria-label^="Send" i]', 'button[aria-label^="Comment" i]',
  'button[aria-label^="Share" i]', 'button[aria-label^="Send" i]',
];
const CONTROL_ATTRIBUTE = 'data-suriph-control';
const POST_SELECTOR = POST_SELECTORS.join(',');
const POST_TEXT_SELECTOR = POST_TEXT_SELECTORS.join(',');
const POST_ACTION_SELECTOR = POST_ACTION_SELECTORS.join(',');
let extensionEnabled = true;
let retrievalEnabled = true;
let interfaceLanguage = 'en';
let activeResultHost = null;
let activeResultDialog = null;
let cachedResultHost = null;

function discardCachedResult(host = cachedResultHost) {
  if (!host) return;
  delete host._suriphResultCache;
  const result = host.shadowRoot?.querySelector('.result');
  result?.replaceChildren();
  if (result) delete result.dataset.mediaChoice;
  if (cachedResultHost === host) cachedResultHost = null;
}

function rememberResult(host, snapshot, mediaChoice) {
  if (cachedResultHost && cachedResultHost !== host) discardCachedResult();
  host._suriphResultCache = { key: postResultCacheKey(snapshot, mediaChoice) };
  const result = host.shadowRoot?.querySelector('.result');
  if (result) result.dataset.mediaChoice = mediaChoice;
  cachedResultHost = host;
}

function positionControlHost(host) {
  host.style.cssText = '';
  host.style.setProperty('position', 'absolute', 'important');
  host.style.setProperty('right', '10px', 'important');
  host.style.setProperty('top', '10px', 'important');
  host.style.setProperty('z-index', '2147483646', 'important');
}

function positionResultOverlay(host) {
  host.style.cssText = '';
  for (const [property, value] of Object.entries({
    position: 'relative',
    width: '100%',
    height: '100%',
    'box-sizing': 'border-box',
    display: 'flex',
    'align-items': 'center',
    'justify-content': 'center',
    background: 'transparent',
    'pointer-events': 'auto',
    visibility: 'visible',
  })) host.style.setProperty(property, value, 'important');
}

function openResultDialog(host) {
  if (activeResultDialog) {
    if (activeResultDialog.open) activeResultDialog.close();
    activeResultDialog.remove();
    activeResultDialog = null;
  }
  const dialog = document.createElement('dialog');
  dialog.setAttribute('aria-label', tr('SuriPH post screening result', 'Resulta ng pagsusuri ng SuriPH'));
  for (const [property, value] of Object.entries({
    position: 'fixed',
    inset: '0',
    width: '100vw',
    height: '100vh',
    'max-width': 'none',
    'max-height': 'none',
    'box-sizing': 'border-box',
    margin: '0',
    padding: '16px',
    border: '0',
    display: 'flex',
    'align-items': 'center',
    'justify-content': 'center',
    overflow: 'auto',
    background: 'rgba(5,23,34,.76)',
    color: 'inherit',
  })) dialog.style.setProperty(property, value, 'important');
  dialog.addEventListener('cancel', event => {
    event.preventDefault();
    host.shadowRoot?.querySelector('.close')?.click();
  });
  document.body.appendChild(dialog);
  dialog.appendChild(host);
  dialog.showModal();
  activeResultDialog = dialog;
}

function closeResultDialog(host) {
  const dialog = activeResultDialog;
  if (!dialog?.contains(host)) return;
  if (dialog.open) dialog.close();
  dialog.remove();
  activeResultDialog = null;
}

function showResult(host, button, message, result) {
  if (activeResultHost && activeResultHost !== host) {
    closeResultDialog(activeResultHost);
    activeResultHost.remove();
    activeResultHost = null;
  }
  activeResultHost = host;
  document.querySelectorAll('#suriph-control-host').forEach(other => { if (other !== host) other.style.visibility = 'hidden'; });
  openResultDialog(host);
  positionResultOverlay(host);
  const wrap = button.closest('.wrap');
  wrap?.classList.add('expanded');
  if (wrap) {
    wrap.style.position = 'relative';
    wrap.style.display = 'flex';
    wrap.style.flexDirection = 'column';
    wrap.style.setProperty('width', 'min(600px, calc(100vw - 32px))', 'important');
    wrap.style.setProperty('max-width', 'calc(100vw - 32px)', 'important');
    wrap.style.setProperty('max-height', 'calc(100vh - 40px)', 'important');
    wrap.style.setProperty('overflow-y', 'auto', 'important');
    wrap.style.setProperty('flex', '0 1 auto', 'important');
    wrap.style.setProperty('background', '#ffffff', 'important');
    wrap.style.color = '#0f172a';
  }
  message.hidden = false;
  result.hidden = false;
  button.style.order = '3';
  button.style.marginTop = '14px';
  message.style.order = '1';
  message.style.color = '#334155';
  result.style.order = '2';
  button.dataset.isOpen = 'true';
  button.title = tr('Check this post again', 'Suriin muli ang post na ito');
  button.setAttribute('aria-label', button.title);
}

function rootsFrom(root = document) {
  const roots = [root];
  for (const element of root.querySelectorAll('*')) {
    if (element.id === 'suriph-control-host') continue;
    if (element.shadowRoot) roots.push(...rootsFrom(element.shadowRoot));
  }
  return roots;
}
function normalize(value) { return (value || '').replace(/\s+/g, ' ').trim(); }
const CAPTION_CONTROL_SELECTOR = '#suriph-control-host, button, [role="button"], nav, form, [aria-expanded][tabindex]';
function readableCaptionText(node) {
  const output = [];
  const boundaryDisplays = new Set([
    'block', 'flex', 'grid', 'list-item', 'table', 'table-row', 'table-cell',
  ]);
  const boundary = () => {
    if (output.length && !/\s$/.test(output[output.length - 1])) output.push(' ');
  };
  const visit = (current) => {
    if (current.nodeType === Node.TEXT_NODE) {
      output.push(current.nodeValue || '');
      return;
    }
    if (current.nodeType !== Node.ELEMENT_NODE) return;
    if (current !== node && current.matches?.(CAPTION_CONTROL_SELECTOR)) return;
    if (current.hidden || current.getAttribute?.('aria-hidden') === 'true') return;
    const style = window.getComputedStyle?.(current);
    if (style?.display === 'none' || style?.visibility === 'hidden') return;
    const separatesText = current.tagName === 'BR' || boundaryDisplays.has(style?.display);
    if (separatesText) boundary();
    if (current.tagName !== 'BR') current.childNodes.forEach(visit);
    if (separatesText) boundary();
  };
  visit(node);
  return normalize(output.join(''));
}
function tr(english, tagalog) { return interfaceLanguage === 'tl' ? tagalog : english; }
const iconPaths = {
  shield: '<path d="M12 2 4.5 5v6c0 5 3.2 8.5 7.5 11 4.3-2.5 7.5-6 7.5-11V5L12 2Z"/><path d="m9 12 2 2 4-4"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  alert: '<path d="M12 3 2 20h20L12 3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
  context: '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 9h8M8 13h8M8 17h5"/>',
  features: '<path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1m8.6 8.6 2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1"/><circle cx="12" cy="12" r="4"/>',
  sources: '<path d="M5 4h11a2 2 0 0 1 2 2v14H7a2 2 0 0 1-2-2V4Z"/><path d="M7 20a2 2 0 0 1 0-4h11M8 8h7M8 11h6"/>',
  text: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  close: '<path d="M5 5 19 19M19 5 5 19"/>',
};
function makeIcon(name) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  node.setAttribute('viewBox', '0 0 24 24'); node.setAttribute('fill', 'none');
  node.setAttribute('stroke', 'currentColor'); node.setAttribute('stroke-width', '1.8');
  node.setAttribute('stroke-linecap', 'round'); node.setAttribute('stroke-linejoin', 'round');
  node.setAttribute('aria-hidden', 'true'); node.innerHTML = iconPaths[name]; return node;
}
function sectionTitle(parent, icon, text, tag = 'h3') {
  const heading = document.createElement(tag); heading.className = 'section-title';
  const mark = document.createElement('span'); mark.className = 'section-icon'; mark.appendChild(makeIcon(icon));
  heading.append(mark, document.createTextNode(text)); parent.appendChild(heading); return heading;
}
function extensionContextAvailable() {
  try { return Boolean(chrome.runtime?.id); } catch (_) { return false; }
}
function isInvalidatedContextError(message) { return /extension context invalidated|context invalidated/i.test(message || ''); }
function localizedError(message) {
  if (isInvalidatedContextError(message)) return tr('SuriPH was updated. Refresh this Facebook tab, then check the post again.', 'Na-update ang SuriPH. I-refresh ang Facebook tab at suriin muli ang post.');
  if (interfaceLanguage !== 'tl') return message || 'SuriPH could not complete the request.';
  if (/speech and story text.*do not match/i.test(message || '')) return 'Hindi nagtugma ang nakuhang salita at teksto sa video. Walang ginawang prediction; pakinggan at suriin ang orihinal na video.';
  if (/middle section.*not transcribed/i.test(message || '')) return 'May bahagi sa gitna ng audio na hindi naisulat. Walang ginawang prediction mula sa kulang na transcript.';
  if (/no reliable speech|no capturable audio track/i.test(message || '')) return 'Walang sapat na nakuhang salita o audio track sa napiling video. Walang ginawang prediction.';
  if (/speech.*clearly|speech quality|uncertain transcript/i.test(message || '')) return 'Hindi malinaw ang ilang salita sa audio kaya walang ginawang prediction. Gumamit ng mas malinaw na clip o piliin ang buong caption.';
  if (/timed out|too long/i.test(message || '')) return 'Nag-timeout ang request. Subukan ang mas maikling content.';
  if (/video|media|capture|image|ocr|transcri/i.test(message || '')) return 'Hindi nakuha o naproseso ang media. Gamitin ang file upload kung kailangan.';
  if (/backend|service|unavailable|connection/i.test(message || '')) return 'Hindi magamit ang SuriPH service. Suriin ang backend at subukan muli.';
  return 'Hindi nakumpleto ng SuriPH ang request. Subukan muli.';
}
function captionGroupCount(container) {
  const messages = [...(container.querySelectorAll?.(POST_TEXT_SELECTOR) || [])];
  return messages.filter((message) => !messages.some((other) => other !== message && other.contains(message))).length;
}
function findPostContainer(node) {
  if (!node?.closest) return null;
  const explicit = node.closest(POST_SELECTOR);
  if (explicit) return explicit;
  const feed = node.closest('[role="feed"], [data-pagelet*="Feed" i], [role="main"]');
  if (!feed) return null;

  // Some Facebook accounts receive a feed layout without article semantics or
  // FeedUnit pagelets. Walk from the recognized caption toward its feed and
  // stop before an ancestor that contains captions from multiple posts.
  let current = node;
  for (let depth = 0; depth < 16 && current?.parentElement; depth += 1) {
    const parent = current.parentElement;
    if (parent.matches?.('[role="dialog"], [role="complementary"]')) return null;
    if (parent === feed) return current;
    if (captionGroupCount(parent) > 1) return current;
    current = parent;
  }
  return null;
}
function findPosts() {
  const posts = [];
  for (const root of rootsFrom()) {
    for (const selector of POST_SELECTORS) for (const element of root.querySelectorAll(selector)) posts.push(element);
    // Caption-first discovery supports Facebook feed variants whose post
    // wrappers do not expose article roles or stable data-pagelet values.
    for (const message of root.querySelectorAll(POST_TEXT_SELECTOR)) {
      const post = findPostContainer(message);
      if (post) posts.push(post);
    }
    // Action rows remain available in layouts where Facebook removes the
    // usual article and caption attributes.
    for (const action of root.querySelectorAll(POST_ACTION_SELECTOR)) {
      const post = findPostContainer(action);
      if (post) posts.push(post);
    }
  }
  const unique = [...new Set(posts)];
  return unique
    .filter((post) => {
      const existingHost = post.querySelector?.('#suriph-control-host');
      const activeOverlayForPost = activeResultHost?.isConnected && activeResultHost._suriphPost === post;
      if (post.hasAttribute(CONTROL_ATTRIBUTE) && (existingHost?.isConnected || activeOverlayForPost)) return false;
      // Recover after an extension reload or an account switch reuses a DOM
      // node but drops the old shadow host.
      if (post.hasAttribute(CONTROL_ATTRIBUTE) && !existingHost && !activeOverlayForPost) post.removeAttribute(CONTROL_ATTRIBUTE);
      const text = normalize(post.innerText || post.textContent || '');
      if (post.closest('[role="dialog"], [role="complementary"], [aria-label*="chat" i], [aria-label*="conversation" i], [data-testid*="chat" i]')) return false;
      // Facebook search/group result cards are not posts and create visual clutter.
      if (/\bjoin\b/i.test(text) && /\bmembers?\b/i.test(text) && !/\bfollow\b/i.test(text)) return false;
      // Standalone comment rows expose role=article too; real post containers usually contain nested rows.
      if (post.matches('[role="article"]') && !post.querySelector('[role="article"]') && /\breply\b/i.test(text)) return false;
      return isEligiblePost(post);
    })
    // If selectors identify nested versions of one post, keep only the outer post container.
    .filter((post) => !unique.some((other) => other !== post && other.contains(post) && other.matches(POST_SELECTOR)));
}
function isEligiblePost(post) {
  if (!post.matches(POST_SELECTOR) || !post.closest(POST_SURFACE_SELECTOR)) return false;
  if (post.closest('[role="dialog"], [role="complementary"], header, footer, [aria-label*="chat" i], [aria-label*="conversation" i], [data-testid*="chat" i], [data-testid*="comment" i], [aria-label^="Comment by" i]')) return false;
  const headings = [...post.querySelectorAll('h1, h2, h3, [role="heading"]')].map(node => normalize(node.innerText || node.textContent || ''));
  const labels = [...post.querySelectorAll('button, [role="button"], a[role="button"]')].map(node => normalize(node.getAttribute('aria-label') || node.innerText || node.textContent || ''));
  const pagelets = [];
  for (let node = post; node && node !== document.body; node = node.parentElement) {
    const pagelet = node.getAttribute?.('data-pagelet');
    if (pagelet) pagelets.push(pagelet);
    if (node.matches?.(POST_SURFACE_SELECTOR)) break;
  }
  if (isRecommendationSurface({ headings, labels, pagelets })) return false;
  const hasAuthor = Boolean(post.querySelector(POST_AUTHOR_SELECTOR));
  const hasTimestampOrPermalink = Boolean(post.querySelector(POST_TIMESTAMP_SELECTOR));
  const hasPostActions = Boolean(post.querySelector(
    '[role="button"][aria-label^="Comment" i], button[aria-label^="Comment" i], [role="button"][aria-label^="Share" i], button[aria-label^="Share" i]',
  ));
  if (!hasAuthor || (!hasTimestampOrPermalink && !hasPostActions)) return false;
  if (collectPostText(post)) return true;
  const media = collectPostMedia(post);
  return media.image_urls.length > 0 || media.has_video;
}
function collectPostText(post) {
  const candidates = [];
  for (const selector of POST_TEXT_SELECTORS) {
    if (post.matches?.(selector)) candidates.push(post);
    post.querySelectorAll?.(selector).forEach(node => candidates.push(node));
  }
  // Several Facebook selectors can identify the same caption or its nested
  // children. Include each visible, owned caption subtree exactly once; a
  // separately authored quoted post or comment must not join this text.
  const owned = [...new Set(candidates)].filter(node => belongsToSelectedPost(post, node)
    && !node.closest?.('#suriph-control-host, button, [role="button"], nav, form'));
  const roots = owned.filter(node => !owned.some(other => other !== node && other.contains(node)));
  const parts = roots.map(readableCaptionText).filter(Boolean);
  if (parts.length) return normalize(parts.join(' '));

  const fallback = [...post.querySelectorAll('[dir="auto"]')].filter(node => {
    if (!belongsToSelectedPost(post, node) || node.closest?.(
      '#suriph-control-host, button, [role="button"], nav, form, header, footer, [aria-hidden="true"], [data-testid*="comment" i], [aria-label^="Comment by" i]',
    )) return false;
    const text = readableCaptionText(node);
    if (!text) return false;
    const style = window.getComputedStyle?.(node);
    return style?.display !== 'none' && style?.visibility !== 'hidden';
  });
  const fallbackRoots = fallback.filter(node => !fallback.some(other => other !== node && other.contains(node)));
  const fallbackText = normalize(fallbackRoots.map(readableCaptionText).filter(Boolean).join(' '));
  if (fallbackText.length >= 24) return fallbackText;

  // Reading the whole article/feed container can include menus, reactions and comments.
  return '';
}
function captionLooksIncomplete(post, text) {
  if (!text) return false;
  if (/(?:\u2026|\.\.\.)\s*$/.test(text)) return true;
  const captions = [...new Set([
    ...post.querySelectorAll(POST_TEXT_SELECTOR),
    ...post.querySelectorAll('[dir="auto"]'),
  ])].filter(caption => belongsToSelectedPost(post, caption));
  return captions.some(caption => [...caption.querySelectorAll('button, [role="button"], [aria-expanded="false"]')]
    .some(control => control.getAttribute('aria-expanded') !== 'true' && /^(?:see|read|show) more$|^(?:tingnan|basahin|magbasa) pa$/i.test(normalize(control.textContent || control.getAttribute('aria-label') || ''))));
}
function postForSelection() {
  const selection = window.getSelection();
  if (!selection?.rangeCount) return null;
  let node = selection.getRangeAt(0).commonAncestorContainer;
  if (node?.nodeType === Node.TEXT_NODE) node = node.parentElement;
  return findPostContainer(node);
}
function postNearestViewport() {
  const activePost = findPostContainer(document.activeElement);
  if (activePost) return activePost;
  const center = window.innerHeight / 2;
  return findPosts()
    .map(post => ({ post, rect: post.getBoundingClientRect() }))
    .filter(({ rect }) => rect.bottom > 0 && rect.top < window.innerHeight && rect.width > 0 && rect.height > 0)
    .sort((left, right) => Math.abs((left.rect.top + left.rect.bottom) / 2 - center) - Math.abs((right.rect.top + right.rect.bottom) / 2 - center))[0]?.post || null;
}
function collectPostContext(post, extractionScope = 'Facebook post caption') {
  const owned = selector => [...post.querySelectorAll(selector)].filter(node => belongsToSelectedPost(post, node));
  const time = owned('time[datetime], time')[0];
  const authorNode = owned(POST_AUTHOR_SELECTOR)[0];
  const rawLinks = owned('a[href]').map(link => link.href).filter(url => /^https?:/i.test(url));
  const isPostLink = (value) => {
    try { const url = new URL(value); return /(^|\.)facebook\.com$/i.test(url.hostname) && (/\/(?:posts|videos|permalink|reel)\//i.test(url.pathname) || url.searchParams.has('story_fbid')); } catch { return false; }
  };
  const originalPostUrl = rawLinks.find(isPostLink) || null;
  const relevantLinks = [];
  for (const value of rawLinks) {
    try {
      const url = new URL(value); const host = url.hostname.toLowerCase();
      const unwrapped = host === 'l.facebook.com' && url.searchParams.get('u') ? new URL(url.searchParams.get('u')).href : url.href;
      const target = new URL(unwrapped); if (target.protocol === 'https:' && !/(^|\.)facebook\.com$/i.test(target.hostname)) relevantLinks.push(target.href);
    } catch (_) {}
  }
  const timestampLink = owned('a[href]').find(link => isPostLink(link.href) && [
    link.getAttribute('aria-label'), link.getAttribute('title'), link.textContent,
  ].some(value => /(?:\b\d+\s*(?:m|min|h|hr|d|w|mo|y)\b|\b20\d{2}\b|\byesterday\b|\btoday\b|\bkahapon\b|\bngayon\b)/i.test(value || '')));
  const epochNode = time || timestampLink;
  const rawEpoch = Number(epochNode?.getAttribute('data-utime'));
  const epochIso = Number.isFinite(rawEpoch) && rawEpoch > 946684800 && rawEpoch < Date.now() / 1000 + 86400
    ? new Date(rawEpoch * 1000).toISOString() : null;
  const dateLabels = [time?.getAttribute('aria-label'), time?.getAttribute('title'),
    timestampLink?.getAttribute('aria-label'), timestampLink?.getAttribute('title'),
    time?.textContent, timestampLink?.textContent].map(normalize).filter(value =>
    /(?:\b\d+\s*(?:m|min|h|hr|d|w|mo|y)\b|\b(?:19|20)\d{2}\b|\byesterday\b|\btoday\b|\bkahapon\b|\bngayon\b|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b)/i.test(value));
  const publishedText = dateLabels.find(value => /\b(?:19|20)\d{2}\b/.test(value)) || dateLabels[0] || null;
  let publishedAt = time?.dateTime || time?.getAttribute('datetime') || epochIso;
  if (!publishedAt && publishedText && /\b(?:19|20)\d{2}\b/.test(publishedText)) {
    const parsed = Date.parse(publishedText.replace(/\s+at\s+/i, ' '));
    if (Number.isFinite(parsed) && parsed <= Date.now() + 86400000) publishedAt = new Date(parsed).toISOString();
  }
  if (!publishedAt && epochIso) publishedAt = epochIso;
  return {
    author: normalize((authorNode?.textContent || '').replace(/\s+follow\b.*$/i, '')) || null,
    published_at: publishedAt || null,
    published_text: publishedText,
    original_post_url: originalPostUrl,
    visible_links: [...new Set(relevantLinks)].slice(0, 8),
    extraction_scope: extractionScope,
  };
}
function findBestVideo(post) {
  const videos = [...post.querySelectorAll('video')].filter(node => ownsMedia(post, node));
  return videos.sort((a, b) => {
    const ar = (b.clientWidth * b.clientHeight) - (a.clientWidth * a.clientHeight);
    return ar || Number(Boolean(b.currentSrc)) - Number(Boolean(a.currentSrc));
  })[0] || null;
}
function ownsMedia(post, node) {
  if (!belongsToSelectedPost(post, node)) return false;
  const style = window.getComputedStyle(node);
  return style.display !== 'none' && style.visibility !== 'hidden'
    && !node.closest('[aria-hidden="true"], [role="complementary"]');
}
function belongsToSelectedPost(post, node) {
  if (!post.contains(node)) return false;
  // Facebook also uses article semantics around a post's own photo/video.
  // A nested article alone is not evidence that the media belongs elsewhere.
  for (let parent = node.parentElement; parent && parent !== post; parent = parent.parentElement) {
    if (parent.matches('[data-testid*="comment" i], [aria-label^="Comment by" i], [aria-label^="Komento ni" i]')) return false;
    if (!parent.matches(POST_SELECTOR)) continue;
    const separateCaption = parent.querySelector(POST_TEXT_SELECTOR)
      || [...parent.querySelectorAll('[dir="auto"]')].some(caption => readableCaptionText(caption));
    const separateAuthor = parent.querySelector(POST_AUTHOR_SELECTOR);
    const commentReply = [...parent.querySelectorAll('button, [role="button"], a')]
      .some(control => /^(?:reply|respond|tumugon|sumagot)$/i.test(normalize(control.textContent || control.getAttribute('aria-label') || '')));
    const outerCaption = [
      ...post.querySelectorAll(POST_TEXT_SELECTOR),
      ...post.querySelectorAll('[dir="auto"]'),
    ].some(caption => !parent.contains(caption) && readableCaptionText(caption).length >= 24);
    const outerAuthor = [...post.querySelectorAll(POST_AUTHOR_SELECTOR)]
      .some(author => !parent.contains(author));
    if (commentReply || (separateCaption && separateAuthor && outerCaption && outerAuthor)) return false;
  }
  return true;
}
function collectPostMedia(post) {
  const images = [...post.querySelectorAll('img[src], img[currentSrc]')]
    .filter(node => ownsMedia(post, node))
    .map((node) => {
      const url = node.currentSrc || node.src;
      const bounds = node.getBoundingClientRect();
      const style = window.getComputedStyle(node);
      try {
        const parsed = new URL(url);
        const allowed = ['facebook.com', 'fbcdn.net', 'fbsbx.com'].some(domain => parsed.hostname === domain || parsed.hostname.endsWith(`.${domain}`));
        if (parsed.protocol !== 'https:' || !allowed || style.display === 'none' || style.visibility === 'hidden' || bounds.width < 120 || bounds.height < 120) return null;
        return { url: parsed.href, area: bounds.width * bounds.height };
      } catch (_) { return null; }
    })
    .filter(Boolean)
    .sort((a, b) => b.area - a.area)
    .map(item => item.url);
  const activeVideo = findBestVideo(post); const video = activeVideo?.currentSrc || activeVideo?.src ? activeVideo : activeVideo?.querySelector('source[src]');
  const videoUrl = video?.currentSrc || video?.src || video?.getAttribute?.('src') || null;
  return { image_urls: [...new Set(images)].slice(0, 4), video_url: /^(https?:|blob:)/i.test(videoUrl || '') ? videoUrl : null, has_video: Boolean(activeVideo || [...post.querySelectorAll('[data-video-id], [aria-label*="video" i]')].some(node => ownsMedia(post, node))) };
}
function setMessage(container, text, tone = 'muted') { container.textContent = text; container.dataset.tone = tone; }
function appendLookupChoice(container) {
  const label = document.createElement('label');
  label.className = 'lookup-choice';
  const checkbox = document.createElement('input'); checkbox.type = 'checkbox'; checkbox.checked = retrievalEnabled;
  const text = document.createElement('span'); text.textContent = tr('Find related articles using Serper and compare readable articles with this claim. A related link alone does not verify the claim.', 'Maghanap ng kaugnay na artikulo gamit ang Serper at ikumpara ang nabasang artikulo sa claim. Hindi sapat ang kaugnay na link para beripikahin ang claim.');
  checkbox.addEventListener('change', () => { retrievalEnabled = checkbox.checked; chrome.storage.local.set({ suriphRetrieveSources: retrievalEnabled }); });
  const disclosure = document.createElement('details'); disclosure.className = 'privacy-notice'; const privacyTitle = document.createElement('summary'); privacyTitle.textContent = tr('Privacy and data processing', 'Privacy at pagproseso ng data'); const privacyText = document.createElement('p'); privacyText.textContent = tr('Classification, evidence reading, and audio transcription run on the SuriPH server using local models. Source search sends a query to Serper and reads public source websites. Do not submit private information.', 'Sa SuriPH server ginagawa ang classification, evidence reading, at audio transcription gamit ang lokal na mga model. Ipinapadala ang source query sa Serper at binabasa ang public source websites. Huwag magsumite ng pribadong impormasyon.'); disclosure.append(privacyTitle, privacyText); container.appendChild(disclosure);
  label.append(checkbox, text); container.appendChild(label);
}
async function captureVisibleVideo(post, options) {
  return captureVideoElement(findBestVideo(post), options);
}
function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer); let binary = ''; const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) binary += String.fromCharCode(...bytes.subarray(index, index + chunkSize));
  return btoa(binary);
}
function analyzeCapturedVideo(videoBase64, payload, onResult, onError, videoUrl = null, onProgress = () => {}) {
  let port;
  try { port = chrome.runtime.connect({ name: 'SURIPH_VIDEO_ANALYSIS' }); }
  catch (error) { onError(error); return () => {}; }
  let finished = false;
  const heartbeat = setInterval(() => {
    if (!finished) {
      try { port.postMessage({ type: 'PING' }); } catch (error) { finish(error); }
    }
  }, 15_000);
  const finish = error => {
    if (finished) return;
    finished = true; clearInterval(heartbeat);
    try { port.disconnect(); } catch (_) {}
    if (error) onError(error);
  };
  port.onMessage.addListener(response => {
    if (finished) return;
    if (response?.type === 'VIDEO_PROGRESS') { onProgress(response.phase); return; }
    if (!response?.ok) {
      const error = new Error(response?.error || 'Video analysis failed.');
      error.fallback_to_capture = response?.fallback_to_capture === true;
      finish(error); return;
    }
    finished = true; clearInterval(heartbeat);
    try { port.disconnect(); } catch (_) {}
    onResult(response);
  });
  port.onDisconnect.addListener(() => {
    if (!finished) finish(new Error(chrome.runtime.lastError?.message || 'The video analysis connection closed before a result was received.'));
  });
  try { port.postMessage({ type: 'ANALYZE_VIDEO', videoBase64, videoUrl, payload }); }
  catch (error) { finish(error); }
  return () => finish();
}
function renderRichResult(container, result) {
  container._suriphResult = result;
  const tl = interfaceLanguage === 'tl';
  const label = result.internal_label === 'Misleading' ? 'Potentially Misleading' : 'No Misleading Information Detected';
  const pct = value => Number.isFinite(value) ? `${(value * 100).toFixed(2)}%` : '—';
  const safeUrl = value => { try { const parsed = new URL(value); return ['https:', 'http:'].includes(parsed.protocol) ? parsed.href : null; } catch (_) { return null; } };
  const section = (part, className = '') => { const node = document.createElement('section'); node.dataset.resultPart = part; node.className = className; container.appendChild(node); return node; };
  const textNode = (parent, tag, text, css = '') => { const node = document.createElement(tag); node.textContent = text; if (css) node.style.cssText = css; parent.appendChild(node); return node; };
  container.replaceChildren();

  const language = document.createElement('div'); language.className = 'language-switch'; language.setAttribute('role', 'group'); language.setAttribute('aria-label', 'Interface language');
  [['English', 'en'], ['Tagalog', 'tl']].forEach(([name, value]) => { const choice = document.createElement('button'); choice.type = 'button'; choice.textContent = name; choice.setAttribute('aria-pressed', String(interfaceLanguage === value)); choice.addEventListener('click', () => { interfaceLanguage = value; chrome.storage.local.set({ suriphLanguage: value }); renderRichResult(container, result); }); language.appendChild(choice); });
  const tools = container.getRootNode().querySelector('.modal-tools'); tools.querySelector('.language-switch')?.remove(); tools.prepend(language);
  container.getRootNode().querySelector('.brand small').textContent = tl ? 'Pagsusuri ng post' : 'Post screening';
  tools.querySelector('.close')?.setAttribute('aria-label', tl ? 'Isara ang resulta' : 'Close result');

  const prediction = section('1-prediction', `status-banner ${result.internal_label === 'Misleading' ? 'warning' : 'clear'}`); const statusLine = document.createElement('div'); statusLine.className = 'status-line'; const statusIcon = document.createElement('span'); statusIcon.className = 'status-icon'; statusIcon.appendChild(makeIcon(result.internal_label === 'Misleading' ? 'alert' : 'check')); const statusText = document.createElement('div'); textNode(statusText, 'small', tl ? 'Resulta ng SuriPH' : 'SuriPH result'); const heading = textNode(statusText, 'strong', label); heading.setAttribute('role', 'status'); statusLine.append(statusIcon, statusText); prediction.appendChild(statusLine);
  const fallbackReason = result.screening_mode === 'evidence_only'
    ? (result.decision_source === 'verified_evidence'
      ? (result.evidence_relationship === 'supports'
        ? (tl ? 'Sapat na mababasang ebidensiya ang sumusuporta sa claim.' : 'Sufficient readable evidence supports the claim.')
        : (tl ? 'May direktang mababasang ebidensiyang sumasalungat sa claim.' : 'Readable evidence directly contradicts the claim.'))
      : (tl ? 'Hindi pa beripikado ang claim. Kailangan pa ng sapat na mapagkakatiwalaang sources o human review.' : 'This claim is not verified yet. More reliable sources or human review are needed.'))
    : result.evidence_relationship === 'conflicting'
    ? (tl ? 'May nabasang source na sumusuporta at may sumasalungat sa claim. Hindi nalutas ang salungatan; hindi beripikado ang model result.' : 'Readable sources both support and contradict this claim. The conflict is unresolved; the model result is unverified.')
    : result.evidence_relationship === 'contradicts'
    ? (tl ? 'May nababasang source na sumasalungat sa claim, pero kailangan ng sapat na ebidensiyang tumutukoy sa mismong claim para baguhin ang label. Model result pa rin ito at hindi beripikadong verdict.' : 'A readable source contradicts the claim, but sufficient claim-specific evidence is required to change the label. The result remains an unverified model output.')
    : Number(result.supporting_source_count) > 0
    ? (tl ? 'May nababasang mapagkakatiwalaang source na sumusuporta, pero kailangan pang pumasa ang ebidensiya sa pagsusuri ng claim at pinagmulan, nang walang mapagkakatiwalaang salungatan. Model result pa rin ito, hindi factual verdict.' : 'A readable trusted article appears to support the claim, but the evidence must meet the claim-specific authority or independent-publisher checks without a trusted contradiction. The result remains an unverified model output, not a factual verdict.')
    : (result.related_sources || []).length > 0
    ? (tl ? 'May kaugnay na link sa ibaba, pero walang nababasang source na direktang nagpatunay sa buong claim. Hindi beripikado ang model result.' : 'The links below are related or unreadable; no readable source established the complete claim. The model result is unverified.')
    : result.internal_label === 'Misleading'
    ? (tl ? 'May nakitang warning signs sa teksto na maaaring nagpapahiwatig ng misleading na impormasyon.' : 'The text check found warning signs that may indicate misleading information.')
    : (tl ? 'Walang sapat na warning signs na nakita sa pagsusuri ng teksto.' : 'The text check did not find enough warning signs to flag this post.');
  const readerNotice = evidenceReaderNotice(result, tl ? 'tl' : 'en');
  const explanation = section('2-explanation'); sectionTitle(explanation, 'info', tl ? 'Bakit ito ang resulta' : 'Why this result'); textNode(explanation, 'p', result.decision_source === 'verified_evidence' ? (result.evidence_relationship === 'supports' ? (tl ? 'May nabasang ebidensiyang sumusuporta sa buong claim at konteksto nito.' : 'Readable evidence supports the complete claim and its context.') : (tl ? 'May nabasang source na direktang sumasalungat sa buong claim.' : 'A readable source directly contradicts the complete claim.')) : (readerNotice || fallbackReason));
  const aiExplanation = tl ? result.evidence_explanation_tl : result.evidence_explanation_en;
  if (result.decision_source === 'verified_evidence' && aiExplanation) {
    const paragraph = [...explanation.children].find(node => node.tagName === 'P');
    if (paragraph) paragraph.textContent = aiExplanation;
  }
  if (result.screening_mode === 'evidence_only') {
    textNode(explanation, 'p', tl ? 'Naka-off ang classifier. Evidence retrieval lang ang ginamit; hindi factual verdict ang hindi pa beripikadong warning.' : 'The classifier is off. This uses evidence retrieval only; an unverified warning is not a factual verdict.');
  } else if (result.decision_source !== 'verified_evidence') {
    textNode(explanation, 'p', tl ? 'Hindi pa verified ang resultang ito gamit ang sapat na ebidensiya; model prediction ito.' : 'This result is not verified by sufficient evidence; it is a model prediction.');
  }
  const context = result.context_explanation || {}; const materialKey = String(context.checked_material || '').toLowerCase(); const hasCaption = Boolean(result.extraction?.caption_text?.trim()); const checkedMaterial = result.extraction?.caption_fallback_used === true ? (tl ? 'Caption lang ng video' : 'Video caption only') : materialKey.includes('video audio transcript') || materialKey.includes('video-frame ocr') ? (hasCaption ? (tl ? 'Caption, salita, at tekstong lumabas sa video' : 'Caption, spoken audio, and text shown in the video') : (tl ? 'Salita at tekstong lumabas sa video' : 'Spoken audio and text shown in the video')) : materialKey.includes('image ocr') ? (hasCaption ? (tl ? 'Caption at tekstong nakita sa image' : 'Caption and text found in the image') : (tl ? 'Tekstong nakita sa image' : 'Text found in the image')) : materialKey.includes('caption') ? (tl ? 'Caption ng post' : 'Post caption') : materialKey.includes('selected') ? (tl ? 'Piniling teksto' : 'Selected text') : context.checked_material; const contextBox = section('3-post-context', 'context-box'); sectionTitle(contextBox, 'context', tl ? 'Tungkol sa post' : 'About this post'); const contextRows = [[tl ? 'Nag-post' : 'Posted by', context.author || (tl ? 'Hindi available' : 'Not available')], [tl ? 'Petsa ng post' : 'Post date', displayPostDate(context, interfaceLanguage)], [tl ? 'Gaano kabago' : 'How recent', displayPostRecency(context, interfaceLanguage)], [tl ? 'Sinuring content' : 'Content checked', checkedMaterial || (tl ? 'Hindi available' : 'Not available')]]; for (const [name, value] of contextRows) { const row = textNode(contextBox, 'p', `${name}: ${value}`); row.className = 'context-row'; }
  const original = safeUrl(context.original_post_url); if (original) { const link = document.createElement('a'); link.href = original; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.textContent = tl ? 'Buksan ang orihinal na post' : 'Open original post'; contextBox.appendChild(link); }

  const featureDescriptions = {
    code_switching_ratio: tl ? 'Paghahalo ng Filipino at English.' : 'Mixing Filipino and English.',
    filipino_particle_frequency: tl ? 'Paggamit ng karaniwang katagang Filipino.' : 'Use of common Filipino connector words.',
    punctuation_intensity: tl ? 'Paggamit ng tandang padamdam at pananong.' : 'Use of exclamation and question marks.',
    capitalization_ratio: tl ? 'Paggamit ng MALALAKING TITIK.' : 'Use of CAPITAL LETTERS.',
    repeated_character_ratio: tl ? 'Paulit-ulit na letra gaya ng “grabeeee”.' : 'Repeated letters such as “wowwww”.',
    emotional_language_frequency: tl ? 'Mga salitang nagpapahayag ng matinding emosyon.' : 'Words that express strong emotion.',
    urgency_cue_frequency: tl ? 'Mga salitang nag-uudyok na kumilos agad.' : 'Words that urge readers to act quickly.',
  };
  const features = document.createElement('details'); features.dataset.resultPart = '4-features'; sectionTitle(features, 'features', tl ? 'Paano sinuri ang teksto' : 'How the text was analyzed', 'summary'); textNode(features, 'p', result.screening_mode === 'evidence_only' ? (tl ? 'Naka-off ang text classifier. Ipinapakita sa ibaba kung anong teksto ang nakuha mula sa caption, image, o video.' : 'The text classifier is off. The extracted caption, image, or video text is shown below.') : (tl ? 'Inilalarawan ng mga sukat na ito ang paraan ng pagkakasulat at paggamit ng wika. Hindi nila pinatutunayan nang mag-isa kung totoo o mali ang post.' : 'These measurements describe the writing style and language. They do not prove by themselves that a post is true or false.')); if (result.screening_mode !== 'evidence_only') { textNode(features, 'p', `${tl ? 'Orihinal na model label' : 'Original model label'}: ${result.model_public_label || label} · ${pct(Number(result.model_score))} ${tl ? 'model score para sa Misleading' : 'Misleading model score'}`); textNode(features, 'small', tl ? 'Hindi ito posibilidad na mali ang claim.' : 'This is not the chance that the claim is false.'); for (const item of result.linguistic_indicators || []) { const row = document.createElement('div'); row.style.cssText = 'padding:8px 0;border-top:1px solid #e2e8f0;'; textNode(row, 'b', `${tl ? item.display_name_tagalog : item.display_name}: ${pct(Number(item.value))}`); textNode(row, 'small', featureDescriptions[item.name] || ''); features.appendChild(row); } } container.appendChild(features);

  const sources = section('5-related-sources', 'sources'); sectionTitle(sources, 'sources', tl ? 'Mga nahanap na source' : 'Sources found'); textNode(sources, 'p', result.decision_source === 'verified_evidence' ? (tl ? 'Inihambing ang buong claim sa nababasang nilalaman ng mga artikulo.' : 'The complete claim was compared with readable article content.') : (tl ? 'Hindi patunay sa buong claim ang link o search preview. Sinusuri lang ang nababasang laman ng artikulo; ihambing ang mga detalye nito sa post.' : 'A link or search preview does not verify the full claim. Only readable article content is assessed; compare its details with the post.'));
  const renderSourceState = () => {
    sources.querySelector('.source-state')?.remove();
    const state = document.createElement('div');
    state.className = 'source-state';
    sources.appendChild(state);
    let rendered = false;
    const checkedUrls = new Set((result.related_sources || [])
      .filter(item => item.content_status === 'readable')
      .map(item => safeUrl(item.url))
      .filter(Boolean));
    const postLinks = [...new Set((context.relevant_links || []).map(safeUrl).filter(Boolean))]
      .filter(href => !checkedUrls.has(href));
    if (postLinks.length) {
      const group = document.createElement('div');
      group.style.cssText = 'padding-top:8px;margin-top:8px;border-top:1px solid #cbd5e1;';
      textNode(group, 'b', tl ? 'Iba pang link na kasama sa post' : 'Other links included in the post');
      textNode(group, 'p', tl
        ? 'Galing sa post ang mga link na ito at hindi sinuri bilang ebidensiya.'
        : 'These links came from the post and were not checked as evidence.');
      for (const href of postLinks) {
        const link = document.createElement('a');
        link.href = href;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = href;
        link.style.cssText = 'display:block;overflow-wrap:anywhere;margin-top:5px;';
        group.appendChild(link);
      }
      state.appendChild(group);
    }
    for (const item of result.fact_check_matches || []) {
      const href = safeUrl(item.url);
      if (!href) continue;
      rendered = true;
      const article = document.createElement('article');
      article.style.cssText = 'padding-top:8px;margin-top:8px;border-top:1px solid #bae6fd;';
      const link = document.createElement('a');
      link.href = href;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = item.title || item.claim || href;
      article.appendChild(link);
      textNode(article, 'small', `${item.publisher || (tl ? 'Hindi nakalagay ang source' : 'Source not listed')} · ${tl ? 'Rating ng fact-check' : 'Fact-check rating'}: ${item.rating}`);
      state.appendChild(article);
    }
    for (const item of result.related_sources || []) {
      const href = safeUrl(item.url);
      if (!href) continue;
      rendered = true;
      const article = document.createElement('article');
      article.style.cssText = 'padding-top:8px;margin-top:8px;border-top:1px solid #bae6fd;';
      const link = document.createElement('a');
      link.href = href;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      const inaccessible = item.content_status === 'inaccessible';
      link.textContent = inaccessible ? item.search_title || href : item.title || href;
      article.appendChild(link);
      textNode(article, 'small', [item.source, item.date].filter(Boolean).join(' · '));
      if (inaccessible) textNode(article, 'small', tl
        ? 'Search result preview lang ito; hindi mabasa ang artikulo kaya hindi ito beripikadong ebidensiya.'
        : 'Search result preview only; the article could not be read, so this is not verified evidence.', 'display:block;margin-top:4px;');
      if (inaccessible && item.search_snippet) textNode(article, 'span', `${tl ? 'Search preview (hindi beripikado)' : 'Search preview (not verified)'}: ${item.search_snippet}`, 'display:block;margin-top:3px;');
      if (!inaccessible && item.snippet) textNode(article, 'span', item.snippet, 'margin-top:3px;');
      if (!inaccessible && item.evidence_excerpt) {
        const passage = document.createElement('details');
        textNode(passage, 'summary', tl ? 'Basahin ang kaugnay na sipi' : 'Read the matching passage');
        textNode(passage, 'blockquote', item.evidence_excerpt, 'white-space:pre-wrap;margin:8px 0;padding-left:12px;border-left:3px solid #0f766e;');
        if (item.used_for_decision) textNode(passage, 'small', tl ? 'Ginamit sa final label; ihambing ang siping ito sa orihinal na post.' : 'Used for the final label; compare this passage with the original post.');
        article.appendChild(passage);
      }
      if (item.relationship === 'conflicting') textNode(article, 'small', tl ? 'May magkasalungat na pahayag sa artikulo; hindi ginamit para baguhin ang label.' : 'Conflicting assertions in this article; not used to change the label.');
      state.appendChild(article);
    }
    if (rendered) return;
    const status = textNode(
      state,
      'span',
      result.retrieval_status === 'not_requested'
        ? (tl ? 'Hindi hiniling ang paghahanap ng sources.' : 'Source search was not requested.')
        : result.retrieval_status === 'no_results'
          ? (tl ? 'Walang nakitang malapit na kaugnay na mapagkakatiwalaang source. Hindi nito awtomatikong ibig sabihin na misleading ang post.' : 'No closely related reliable source was found. This alone does not mean the post is misleading.')
          : (tl ? 'Pansamantalang hindi magamit ang paghahanap ng sources.' : 'Reliable-source search is temporarily unavailable.'),
    );
    if (result.retrieval_status === 'not_requested') {
      const find = document.createElement('button');
      find.type = 'button';
      find.textContent = tl ? 'Maghanap ng kaugnay na sources' : 'Find related sources';
      find.style.cssText = 'width:100%;margin-top:10px;padding:9px;border:1px solid #0f766e;border-radius:8px;background:#fff;color:#0f766e;font-weight:700;cursor:pointer;';
      find.addEventListener('click', () => {
        find.disabled = true;
        status.textContent = tl ? 'Naghahanap ng kaugnay na sources…' : 'Finding related sources…';
        chrome.runtime.sendMessage({ type: 'SURIPH_LOOKUP_SOURCES', payload: { text: result.analyzed_text, page_url: result.page_url } }, response => {
          if (!container.isConnected || container._suriphResult !== result || activeResultHost !== container.getRootNode().host) return;
          if (chrome.runtime.lastError || !response?.ok) {
            result.retrieval_status = 'request_failed';
          } else {
            Object.assign(result, mergeRelatedSources(result, result, response.result));
          }
          retrievalEnabled = true;
          chrome.storage.local.set({ suriphRetrieveSources: true });
          renderRichResult(container, result);
        });
      });
      state.appendChild(find);
    }
  };
  renderSourceState();
  if (result.search_grounding) {
    const grounding = document.createElement('div');
    textNode(grounding,'h4',tl ? 'Mga search reference' : 'Search references');
    textNode(grounding,'p',tl ? 'Mga reference mula sa search grounding; hiwalay sa nasuring article passages.' : 'Search-grounding references; separate from checked article passages.');
    for (const item of result.search_grounding.sources || []) {
      const href=safeUrl(item.url); if (!href) continue;
      const link=document.createElement('a'); link.href=href; link.textContent=item.title;link.target='_blank';link.rel='noopener noreferrer';grounding.appendChild(link);grounding.appendChild(document.createElement('br'));
    }
    if (result.search_grounding.search_suggestions_html) {
      const frame=document.createElement('iframe');frame.title='Search suggestions';frame.setAttribute('sandbox','allow-popups allow-popups-to-escape-sandbox');frame.referrerPolicy='no-referrer';frame.srcdoc=result.search_grounding.search_suggestions_html;frame.style.cssText='width:100%;height:140px;border:0;';grounding.appendChild(frame);
    }
    sources.appendChild(grounding);
  }
  const sourceCards = sources.querySelectorAll('.source-state > article');
  const sourceOffset = (result.fact_check_matches || []).filter(item => safeUrl(item.url)).length;
  (result.related_sources || []).filter(item => safeUrl(item.url)).forEach((item, index) => {
    const card = sourceCards[sourceOffset + index]; if (!card) return;
    if (item.relationship === 'supports' && item.decision_eligible === false) {
      textNode(card, 'small', tl ? 'May kaugnay na suportang konteksto, pero hindi sapat para baguhin ang label.' : 'Supporting context was found, but it is insufficient to change the label.');
      return;
    }
    if (item.content_status !== 'inaccessible') {
      const detail = tl ? item.relationship_reason_tl : item.relationship_reason;
      if (detail) textNode(card, 'p', detail);
    }
    textNode(card, 'small', item.relationship === 'supports' ? (tl ? 'Sinusuportahan ang buong claim' : 'Supports the complete claim') : item.relationship === 'contradicts' ? (tl ? 'Sumasalungat sa buong claim' : 'Contradicts the complete claim') : item.content_status === 'inaccessible' ? (tl ? 'Hindi mabasa ang artikulo; walang excerpt' : 'Article inaccessible; no excerpt available') : (tl ? 'Kaugnay na balita; hindi pa napatunayan ang claim' : 'Related coverage; claim not established'));
  });

  const analyzed = document.createElement('details'); analyzed.dataset.resultPart = '6-analyzed-text'; sectionTitle(analyzed, 'text', tl ? 'Tekstong sinuri' : 'Text checked', 'summary'); textNode(analyzed, 'p', tl ? 'Ito ang eksaktong tekstong sinuri ng SuriPH.' : 'This is the exact text SuriPH checked.', 'font-size:12px;color:#475569;'); textNode(analyzed, 'p', result.analyzed_text || '', 'white-space:pre-wrap;overflow-wrap:anywhere;'); container.appendChild(analyzed);
  if (result.extraction) {
    // Keep the exact combined input available, but identify each media source
    // so OCR is never presented as something a person said in the video.
    const combinedText = analyzed.lastElementChild;
    combinedText.remove();
    const extraction = result.extraction;
    const incomplete = incompleteVideoNotice(extraction, interfaceLanguage);
    if (incomplete) textNode(analyzed, 'p', incomplete, 'color:#9a3412;');
    const parts = [
      [tl ? 'Caption ng post' : 'Post caption', extraction.caption_text],
      [tl ? 'Mga salitang narinig sa video' : 'Speech heard in the video', extraction.transcript_text],
      [tl ? 'Tekstong nakita sa mga frame' : 'Text found in sampled video frames', extraction.frame_ocr_text],
      [tl ? 'Tekstong nakita sa image' : 'Text found in the image', extraction.ocr_text],
    ];
    for (const [title, text] of parts) if (text?.trim()) { textNode(analyzed, 'h4', title); textNode(analyzed, 'p', text, 'white-space:pre-wrap;overflow-wrap:anywhere;'); }
    if (Array.isArray(extraction.frame_ocr_regions) && extraction.frame_ocr_regions.length) { const timed = document.createElement('details'); const heading = document.createElement('summary'); heading.textContent = tl ? 'Teksto ayon sa oras ng frame' : 'Frame text by timestamp'; timed.appendChild(heading); for (const region of extraction.frame_ocr_regions) if (region.text) textNode(timed, 'p', `${Number(region.sample_seconds || 0).toFixed(1)}s: ${region.text}`); analyzed.appendChild(timed); }
    if (extraction.caption_only === true) textNode(analyzed, 'p', tl ? 'Caption ng post lang ang sinuri. Hindi sinuri ang audio o mga frame ng video.' : 'Only the post caption was checked. Video audio and frames were not analyzed.');
    if ('transcript_text' in extraction && !extraction.transcript_text && extraction.transcript_status !== 'not_requested') textNode(analyzed, 'p', tl ? 'Walang malinaw na salita na nakuha mula sa audio. Hindi pinunan ng gawa-gawang transcript.' : 'No reliable speech was extracted from the audio. No transcript was invented.');
    if (extraction.quality_notice) textNode(analyzed, 'small', tl ? 'Ihambing ang nakuha sa orihinal na video. Maaaring may maling salita o hindi nakuha; piling video frames lang ang sinuri.' : 'Compare the extracted text with the original video. Words may be missed or misread; only sampled frames were checked.');
    if (extraction.discarded_ocr_detections > 0) textNode(analyzed, 'small', tl ? 'Hindi isinama ang ilang tekstong hindi malinaw basahin.' : 'Some low-confidence image text was excluded.');
    const combined = document.createElement('details'); textNode(combined, 'summary', tl ? 'Pinagsamang tekstong sinuri' : 'Combined text used for the check'); combined.appendChild(combinedText); analyzed.appendChild(combined);
  }
  const reminder = section('7-reminder', 'disclaimer'); const infoMark = document.createElement('span'); infoMark.className = 'section-icon'; infoMark.appendChild(makeIcon('info')); reminder.appendChild(infoMark); reminder.appendChild(document.createTextNode(tl ? 'Maaaring magkamali ang SuriPH. Basahin ang buong post, tingnan ang petsa at pinagmulan, at ikumpara ito sa mapagkakatiwalaang sanggunian bago ibahagi o aksyunan.' : 'SuriPH can make mistakes. Read the full post, check its date and source, and compare it with reliable references before sharing or acting on it.'));
  container.dataset.tone = result.internal_label === 'Misleading' ? 'warn' : 'safe';
}
function renderVideoAcquisitionChoice({ post, button, message, result, snapshot, isCurrent, showRequestError, selectedVideo, selectedVideoSource }) {
  result.replaceChildren();
  const card = document.createElement('section'); card.className = 'review-card';
  const title = document.createElement('strong'); title.textContent = tr('Direct video access is unavailable', 'Hindi direktang makuha ang video');
  const note = document.createElement('p'); note.textContent = tr(
    'Choose the complete post caption, or capture the selected video while it plays. No audio has been analyzed yet.',
    'Piliin ang kumpletong caption, o kunin ang napiling video habang nagpe-play ito. Wala pang nasuring audio.');
  card.append(title, note);
  const canUseCaption = usableVideoCaption(snapshot.submittedText, !snapshot.captionOmitted);
  const choices = document.createElement('div'); choices.className = 'choice-grid';
  const choose = (label, mode) => {
    const action = document.createElement('button'); action.type = 'button';
    action.className = mode === 'caption' ? 'primary-button' : 'secondary-button'; action.textContent = label;
    action.disabled = mode === 'caption' && !canUseCaption;
    action.addEventListener('click', () => {
      if (!isCurrent()) return;
      if (!post.isConnected || collectPostText(post) !== snapshot.text || location.href !== snapshot.pageUrl
          || findBestVideo(post) !== selectedVideo || (selectedVideo?.currentSrc || selectedVideo?.src || '') !== selectedVideoSource) {
        showRequestError(new Error('The selected post or video changed. Check it again.')); return;
      }
      analyzePost(post, button, message, result, 'video', { ...snapshot, videoAcquisitionChoice: mode });
    });
    choices.appendChild(action);
  };
  choose(tr('Caption only', 'Caption lang'), 'caption');
  choose(tr('Caption and video', 'Caption at video'), 'capture');
  card.appendChild(choices);
  const help = document.createElement('p'); help.className = 'chooser-note';
  help.textContent = canUseCaption
    ? tr('If speech is unclear, only the complete caption will be checked. Text checked will show the basis used.', 'Kung hindi malinaw ang speech, kumpletong caption lang ang susuriin. Makikita sa Tekstong sinuri ang ginamit na basehan.')
    : tr('No complete, informative caption is available. Video capture is required; a collapsed caption is not used as a fallback.', 'Walang kumpleto at sapat na caption. Kailangan ang video capture; hindi gagamitin ang putol na caption bilang fallback.');
  card.appendChild(help); appendLookupChoice(card); result.appendChild(card);
  button.disabled = false; button.textContent = tr('Check again', 'Suriin muli'); setMessage(message, '');
}

function renderVideoReview({ post, button, message, result, preview, snapshot, isCurrent, showRequestError }) {
  const extraction = preview?.extraction;
  if (!matchesVideoPreview(preview, {
    text: snapshot.submittedText, pageUrl: snapshot.pageUrl, pageTitle: snapshot.pageTitle,
  })) {
    showRequestError(new Error('The extracted video text did not match this post.'));
    return;
  }
  result.replaceChildren();
  const card = document.createElement('section'); card.className = 'review-card video-review';
  const title = document.createElement('b'); title.textContent = tr('Review the video extraction', 'Suriin muna ang nakuhang teksto sa video');
  const note = document.createElement('p'); note.textContent = tr(
    'Listen to the selected video and compare names, places, dates, amounts, negation, and allegations. SuriPH has not classified this text yet.',
    'Pakinggan ang napiling video at ihambing ang mga pangalan, lugar, petsa, halaga, pagtanggi, at paratang. Hindi pa ito kinlasipika ng SuriPH.');
  card.append(title, note);
  if (snapshot.captionOmitted) {
    const captionNotice = document.createElement('p'); captionNotice.className = 'status';
    captionNotice.textContent = tr('The Facebook caption was collapsed and was not included. Only extracted video content will be checked.', 'Naka-collapse ang caption ng Facebook kaya hindi ito isinama. Ang nakuhang laman ng video lang ang susuriin.');
    card.appendChild(captionNotice);
  }
  const incomplete = incompleteVideoNotice(extraction, interfaceLanguage);
  if (incomplete) {
    const warning = document.createElement('p'); warning.className = 'status error';
    warning.textContent = incomplete; card.appendChild(warning);
  }
  if (extraction.speech_frame_agreement === 'review_required') {
    const warning = document.createElement('p'); warning.className = 'status error';
    warning.textContent = tr(
      'The speech and on-screen wording differ. They may use different languages. Compare both with the video before confirming.',
      'Magkaiba ang mga salita sa audio at sa screen. Maaaring magkaiba ang wika nila. Ihambing ang dalawa sa video bago kumpirmahin.');
    card.appendChild(warning);
  }
  const addSection = (heading, value) => {
    const label = document.createElement('strong'); label.className = 'review-section-label'; label.textContent = heading;
    const body = document.createElement('p'); body.className = 'review-text'; body.textContent = value || tr('None detected', 'Walang nakuha');
    card.append(label, body);
  };
  addSection(tr('Speech heard in the video', 'Salitang narinig sa video'), extraction.transcript_text);
  const frameLines = Array.isArray(extraction.frame_ocr_regions) && extraction.frame_ocr_regions.length
    ? extraction.frame_ocr_regions.map(item => `${Number(item.sample_seconds).toFixed(1)}s · ${item.text}`).join('\n')
    : extraction.frame_ocr_text;
  addSection(tr('Relevant on-screen text', 'Kaugnay na tekstong nasa screen'), frameLines);
  if (extraction.frame_ocr_included === false && extraction.frame_ocr_text) {
    const notice = document.createElement('p'); notice.className = 'status error';
    notice.textContent = tr(
      'On-screen text is shown for review but will not be classified because it could not be tied to the speech.',
      'Ipinakita ang text sa screen para masuri mo, pero hindi ito isasama sa prediction dahil hindi matiyak na kaugnay ito ng audio.');
    card.appendChild(notice);
  }
  const actions = document.createElement('div'); actions.className = 'review-actions';
  const reject = document.createElement('button'); reject.type = 'button'; reject.className = 'secondary-button';
  reject.textContent = tr('Text is wrong — no prediction', 'Mali ang teksto — walang prediction');
  const confirm = document.createElement('button'); confirm.type = 'button'; confirm.className = 'primary-button';
  confirm.textContent = tr('Text matches — analyze it', 'Tugma ang teksto — suriin ito');
  reject.addEventListener('click', () => {
    if (!isCurrent()) return;
    result.replaceChildren(); button.disabled = false; button.textContent = tr('Check again', 'Suriin muli');
    setMessage(message, tr('Video extraction was rejected. No prediction was made.', 'Tinanggihan ang nakuhang teksto sa video. Walang ginawang prediction.'), 'error');
  });
  confirm.addEventListener('click', () => {
    if (!isCurrent() || !post.isConnected || collectPostText(post) !== snapshot.text
        || location.href !== snapshot.pageUrl) {
      result.replaceChildren(); showRequestError(new Error('This Facebook post changed during video review. Check it again.')); return;
    }
    const currentContext = collectPostContext(post, 'Facebook post video');
    if ((snapshot.context?.original_post_url || '') !== (currentContext.original_post_url || '')
        || (snapshot.context?.author || '') !== (currentContext.author || '')) {
      result.replaceChildren(); showRequestError(new Error('The selected Facebook post changed during video review.')); return;
    }
    confirm.disabled = true; reject.disabled = true;
    setMessage(message, tr('Checking the confirmed video text...', 'Sinusuri ang kinumpirmang teksto sa video...'), 'loading');
    chrome.runtime.sendMessage({ type: 'SURIPH_CONFIRM_VIDEO', payload: {
      review_token: preview.review_token, confirmed: true,
      transcript_text: extraction.transcript_text, frame_ocr_text: extraction.frame_ocr_text,
    } }, response => {
      if (!isCurrent()) return;
      const runtimeError = chrome.runtime.lastError;
      if (runtimeError || !response?.ok || !matchesSubmittedPost(response.result, {
        text: snapshot.submittedText, mediaChoice: 'video', pageUrl: snapshot.pageUrl, pageTitle: snapshot.pageTitle,
      })) {
        result.replaceChildren(); showRequestError(new Error(runtimeError?.message || response?.error || 'The returned text did not match this post.'));
        return;
      }
      button.disabled = false; button.textContent = tr('Check again', 'Suriin muli');
      button.dataset.recheck = 'true'; button.dataset.resultPart = '8-check-again';
      setMessage(message, ''); renderRichResult(result, response.result);
      rememberResult(button.getRootNode().host, snapshot, 'video');
    });
  });
  actions.append(reject, confirm); card.appendChild(actions); result.appendChild(card);
  button.disabled = false; button.textContent = tr('Check again', 'Suriin muli'); setMessage(message, '');
}
function renderMediaChooser(post, button, message, result, media, snapshot) {
  result.replaceChildren();
  const title = document.createElement('strong'); title.className = 'chooser-title'; title.textContent = tr('What would you like SuriPH to check?', 'Ano ang gusto mong suriin ng SuriPH?'); result.appendChild(title);
  const note = document.createElement('span'); note.className = 'chooser-note'; note.textContent = tr('This post contains media. Choose the media itself or the caption.', 'May media ang post na ito. Piliin ang media o ang caption.'); result.appendChild(note);
  if (captionLooksIncomplete(post, snapshot.text)) {
    const captionNotice = document.createElement('span'); captionNotice.className = 'chooser-note';
    captionNotice.textContent = tr('The caption is collapsed. A media check will use the image/video only; expand the caption if you want its text included.', 'Naka-collapse ang caption. Ang image/video lang ang susuriin; buksan ang buong caption kung gusto mong isama ang teksto nito.');
    result.appendChild(captionNotice);
  }
  appendLookupChoice(result);
  const choices = document.createElement('div'); choices.className = 'choice-grid';
  const addChoice = (label, mode) => { const choice = document.createElement('button'); choice.type = 'button'; choice.textContent = label; choice.className = choices.children.length ? 'secondary-button' : 'primary-button'; choice.addEventListener('click', () => { result.replaceChildren(); analyzePost(post, button, message, result, mode, snapshot); }); choices.appendChild(choice); };
  if (media.has_video) addChoice(tr('Check this video', 'Suriin ang video'), 'video');
  if (media.image_urls?.length) addChoice(tr('Check this image', 'Suriin ang image'), 'image');
  addChoice(tr('Check caption/text', 'Suriin ang caption/teksto'), 'text'); result.appendChild(choices);
}
function analyzePost(post, button, message, result, mediaChoice = 'auto', lockedSnapshot = null) {
  discardCachedResult();
  result._suriphResult = null;
  delete button.dataset.resultPart;
  if (button.dataset.recheck === 'true') { delete button.dataset.previewConfirmed; button.dataset.recheck = 'false'; }
  const host = button.getRootNode().host;
  showResult(host, button, message, result);
  const snapshot = lockedSnapshot || { text: collectPostText(post), media: collectPostMedia(post), context: collectPostContext(post, 'Facebook post caption'), pageUrl: location.href, pageTitle: document.title };
  if (!post.isConnected || (lockedSnapshot && collectPostText(post) !== snapshot.text)) { button.disabled = false; setMessage(message, tr('This Facebook post changed while it was being prepared. Check it again.', 'Nagbago ang Facebook post habang inihahanda. Suriin itong muli.'), 'error'); return; }
  const screeningMode = resolveMediaChoice(mediaChoice, snapshot.media);
  if (screeningMode === 'choose') { setMessage(message, ''); renderMediaChooser(post, button, message, result, snapshot.media, snapshot); return; }
  if (screeningMode === 'unavailable') {
    button.disabled = false; button.textContent = tr('Check again', 'Suriin muli');
    setMessage(message, tr('The selected media is no longer available in this post. No prediction was made.', 'Hindi na makita ang napiling media sa post na ito. Walang ginawang prediction.'), 'error');
    return;
  }
  result.replaceChildren();
  button.disabled = true; button.textContent = tr('Checking…', 'Sinusuri…'); setMessage(message, tr('SuriPH is checking this post and its available context…', 'Sinusuri ng SuriPH ang post at available na konteksto…'), 'loading');
  const progress = [tr('SuriPH is reading the post context...', 'Binabasa ng SuriPH ang konteksto ng post...'), screeningMode === 'video' ? tr('SuriPH is processing video frames and speech...', 'Pinoproseso ng SuriPH ang mga frame at salita sa video...') : screeningMode === 'image' ? tr('SuriPH is reading the image and its text...', 'Binabasa ng SuriPH ang image at teksto nito...') : tr('SuriPH is checking the post and its context...', 'Sinusuri ng SuriPH ang post at konteksto nito...')];
  let progressIndex = 0; let videoPhase = null; const startedAt = Date.now(); setMessage(message, progress[progressIndex], 'loading');
  let timedOut = false; let cancelVideoAnalysis = null; const progressTimer = setInterval(() => { if (!isCurrent()) { clearInterval(progressTimer); return; } progressIndex = (progressIndex + 1) % progress.length; const elapsed = Math.round((Date.now() - startedAt) / 1000); setMessage(message, `${videoPhase || progress[progressIndex]} (${elapsed}s)`, 'loading'); }, 2200);
  const hardTimeout = setTimeout(() => { if (!isCurrent()) { clearInterval(progressTimer); return; } timedOut = true; cancelVideoAnalysis?.(); clearInterval(progressTimer); button.disabled = false; button.textContent = tr('Check again', 'Suriin muli'); setMessage(message, tr('Video processing took too long and was stopped. Try a shorter video or upload the file through the popup.', 'Masyadong matagal ang pagproseso ng video. Subukan ang mas maikling video o i-upload ang file sa popup.'), 'error'); }, screeningMode === 'video' ? 600000 : 300000);
  const requestEpoch = String(Number(host.dataset.requestEpoch || 0) + 1); host.dataset.requestEpoch = requestEpoch;
  const isCurrent = () => host.dataset.requestEpoch === requestEpoch && activeResultHost === host && host.isConnected;
  const showRequestError = (error) => {
    clearInterval(progressTimer); clearTimeout(hardTimeout);
    button.disabled = false;
    const invalidated = isInvalidatedContextError(error?.message) || !extensionContextAvailable();
    button.dataset.needsReload = invalidated ? 'true' : 'false';
    button.textContent = invalidated ? tr('Refresh Facebook tab', 'I-refresh ang Facebook tab') : tr('Check again', 'Suriin muli');
    setMessage(message, localizedError(invalidated ? 'Extension context invalidated.' : error?.message), 'error');
  };
  if (!extensionContextAvailable()) { showRequestError(new Error('Extension context invalidated.')); return; }
  const text = snapshot.text;
  const captionComplete = !captionLooksIncomplete(post, text);
  const submittedText = captionForScreening(text, captionComplete, screeningMode);
  snapshot.submittedText = submittedText;
  snapshot.captionOmitted = Boolean(text && !captionComplete && screeningMode !== 'text');
  const media = snapshot.media;
  const acquisitionContext = { ...snapshot.context, extraction_scope: screeningMode === 'video' ? 'Facebook post video audio transcript and video-frame OCR' : screeningMode === 'image' ? 'Facebook post image OCR' : 'Facebook post caption' };
  acquisitionContext.caption_complete = !submittedText || captionComplete;
  if (screeningMode === 'text' && !captionComplete && submittedText) { clearTimeout(hardTimeout); clearInterval(progressTimer); button.disabled = false; button.textContent = tr('Check with SuriPH', 'Suriin gamit ang SuriPH'); setMessage(message, tr('The caption looks incomplete. Expand See more, then try again.', 'Mukhang kulang ang caption. Buksan ang See more, saka subukan muli.'), 'error'); return; }
  const selectedMedia = screeningMode === 'video' ? { video_url: media.video_url, has_video: media.has_video } : screeningMode === 'image' ? { image_urls: media.image_urls } : {};
  if (!text && screeningMode === 'text') { clearTimeout(hardTimeout); clearInterval(progressTimer); button.disabled = false; button.textContent = tr('Check with SuriPH', 'Suriin gamit ang SuriPH'); setMessage(message, tr('No readable Facebook post caption or text was found.', 'Walang nakitang mababasang caption o teksto ng Facebook post.'), 'error'); return; }
  if (text && screeningMode === 'text' && button.dataset.previewConfirmed !== 'true') {
    clearTimeout(hardTimeout); clearInterval(progressTimer); button.disabled = false; button.textContent = tr('Check with SuriPH', 'Suriin gamit ang SuriPH'); setMessage(message, tr('Review the exact text that will be checked against reliable sources.', 'Basahin muna ang eksaktong tekstong ihahambing sa mapagkakatiwalaang sources.'));
    const preview = document.createElement('section'); preview.className = 'review-card';
    const title = document.createElement('b'); title.textContent = interfaceLanguage === 'tl' ? 'Tekstong susuriin' : 'Text to check';
    const body = document.createElement('p'); body.className = 'review-text'; body.textContent = text;
    const confirm = document.createElement('button'); confirm.type = 'button'; confirm.className = 'primary-button'; confirm.textContent = interfaceLanguage === 'tl' ? 'Suriin ang tekstong ito' : 'Analyze this text';
    confirm.addEventListener('click', () => { button.dataset.previewConfirmed = 'true'; result.replaceChildren(); analyzePost(post, button, message, result, mediaChoice, snapshot); });
    preview.append(title, body); appendLookupChoice(preview); preview.appendChild(confirm); result.appendChild(preview); return;
  }
  if (screeningMode === 'video') {
    const selectedVideo = findBestVideo(post);
    const selectedVideoSource = selectedVideo?.currentSrc || selectedVideo?.src || '';
    const payload = {
      text: submittedText, page_url: snapshot.pageUrl, page_title: snapshot.pageTitle,
      context: acquisitionContext, retrieve_sources: retrievalEnabled,
    };
    const handleVideoResult = response => {
      if (timedOut || !isCurrent()) return;
      if (collectPostText(post) !== text || findBestVideo(post) !== selectedVideo
          || (selectedVideo?.currentSrc || selectedVideo?.src || '') !== selectedVideoSource) {
        showRequestError(new Error('The selected post or video changed during analysis.')); return;
      }
      clearInterval(progressTimer); clearTimeout(hardTimeout);
      if (response?.result?.review_required) {
        renderVideoReview({ post, button, message, result, preview: response.result, snapshot,
          isCurrent, showRequestError });
        return;
      }
      button.disabled = false; button.textContent = tr('Check again', 'Suriin muli');
      if (!matchesSubmittedPost(response.result, {
        text: submittedText, mediaChoice: 'video', pageUrl: snapshot.pageUrl, pageTitle: snapshot.pageTitle,
      })) { showRequestError(new Error('The returned video result did not match the selected post.')); return; }
      setMessage(message, ''); button.dataset.recheck = 'true'; button.dataset.resultPart = '8-check-again';
      renderRichResult(result, response.result);
      rememberResult(button.getRootNode().host, snapshot, 'video');
    };
    const captureAndAnalyze = () => {
      if (timedOut || !isCurrent()) return;
      videoPhase = tr('Direct video access is unavailable. Capturing the selected video in real time; file upload avoids this wait.', 'Hindi direktang makuha ang video. Kinukuha ito habang nagpe-play; makakaiwas sa hintay na ito gamit ang file upload.');
      setMessage(message, videoPhase, 'loading');
      captureVisibleVideo(post, {
        shouldContinue: () => !timedOut && isCurrent(),
        onProgress: ({ capturedSeconds, durationSeconds }) => {
          videoPhase = tr(`Capturing selected video: ${Math.floor(capturedSeconds)} / ${Math.ceil(durationSeconds)} seconds. Speech processing follows.`, `Kinukuha ang napiling video: ${Math.floor(capturedSeconds)} / ${Math.ceil(durationSeconds)} segundo. Susunod ang speech processing.`);
        },
      }).then(blob => {
        if (timedOut || !isCurrent() || collectPostText(post) !== text) return null;
        if (blob.size > 50 * 1024 * 1024) throw new Error('Media exceeds the 50 MiB limit.');
        videoPhase = tr('Transcribing speech and reading sampled frames...', 'Kinukuha ang salita at binabasa ang piling frame...');
        setMessage(message, videoPhase, 'loading');
        return blob.arrayBuffer();
      }).then(arrayBuffer => {
        if (!arrayBuffer || timedOut || !isCurrent()) return;
        cancelVideoAnalysis = analyzeCapturedVideo(arrayBufferToBase64(arrayBuffer), payload,
          handleVideoResult, error => { if (!timedOut && isCurrent()) showRequestError(error); });
      }).catch(error => { if (!timedOut && isCurrent()) showRequestError(error); });
    };
    const showAcquisitionChoice = () => {
      if (timedOut || !isCurrent()) return;
      clearInterval(progressTimer); clearTimeout(hardTimeout);
      renderVideoAcquisitionChoice({ post, button, message, result, snapshot, isCurrent, showRequestError,
        selectedVideo, selectedVideoSource });
    };
    if (snapshot.videoAcquisitionChoice === 'caption') {
      videoPhase = tr('Checking the complete video post caption...', 'Sinusuri ang kumpletong caption ng video post...');
      setMessage(message, videoPhase, 'loading');
      chrome.runtime.sendMessage({ type: 'SURIPH_ANALYZE_VIDEO_CAPTION', payload }, response => {
        if (timedOut || !isCurrent()) return;
        if (!post.isConnected || collectPostText(post) !== text || findBestVideo(post) !== selectedVideo
            || (selectedVideo?.currentSrc || selectedVideo?.src || '') !== selectedVideoSource || location.href !== snapshot.pageUrl) {
          showRequestError(new Error('The selected post or video changed during analysis.')); return;
        }
        const error = chrome.runtime.lastError;
        if (error || !response?.ok || !matchesSubmittedPost(response.result, {
          text: submittedText, mediaChoice: 'video-caption', pageUrl: snapshot.pageUrl, pageTitle: snapshot.pageTitle,
        })) { showRequestError(new Error(error?.message || response?.error || 'The returned caption result did not match the selected post.')); return; }
        clearInterval(progressTimer); clearTimeout(hardTimeout);
        button.disabled = false; button.textContent = tr('Check again', 'Suriin muli');
        button.dataset.recheck = 'true'; button.dataset.resultPart = '8-check-again'; setMessage(message, '');
        renderRichResult(result, response.result); rememberResult(host, snapshot, 'video-caption');
      });
      return;
    }
    if (snapshot.videoAcquisitionChoice === 'capture') { captureAndAnalyze(); return; }
    if (/^https:\/\//i.test(media.video_url || '')) {
      videoPhase = tr('Trying a direct video download and analysis...', 'Sinusubukang direktang kunin at suriin ang video...');
      setMessage(message, videoPhase, 'loading');
      cancelVideoAnalysis = analyzeCapturedVideo(null, payload, handleVideoResult, error => {
        if (timedOut || !isCurrent()) return;
        if (error.fallback_to_capture) showAcquisitionChoice();
        else showRequestError(error);
      }, media.video_url, phase => {
        if (timedOut || !isCurrent()) return;
        videoPhase = phase === 'extracting'
          ? tr('Video downloaded. Transcribing its audio and reading sampled frames...', 'Nakuha na ang video. Kinukuha ang salita sa audio at binabasa ang piling frame...')
          : tr('Downloading the selected video without real-time playback...', 'Direktang kinukuha ang napiling video nang hindi hinihintay ang buong playback...');
        setMessage(message, videoPhase, 'loading');
      });
    } else showAcquisitionChoice();
    return;
  }
  try { chrome.runtime.sendMessage({ type: 'SURIPH_ANALYZE_TEXT', payload: { text: submittedText, page_url: snapshot.pageUrl, page_title: snapshot.pageTitle, context: acquisitionContext, media: selectedMedia, retrieve_sources: retrievalEnabled } }, (response) => {
    clearInterval(progressTimer);
    if (timedOut || !isCurrent()) return; clearTimeout(hardTimeout); let runtimeError; try { runtimeError = chrome.runtime.lastError; } catch (error) { showRequestError(error); return; } button.disabled = false; button.textContent = tr('Check again', 'Suriin muli');
    if (runtimeError || !response?.ok || !matchesSubmittedPost(response.result, { text: submittedText, mediaChoice, pageUrl: snapshot.pageUrl, pageTitle: snapshot.pageTitle })) { showRequestError(new Error(runtimeError?.message || response?.error || 'The returned text did not match this post.')); return; }
    setMessage(message, '');

    button.dataset.recheck = 'true';
    button.dataset.resultPart = '8-check-again';
    renderRichResult(result, response.result);
    rememberResult(button.getRootNode().host, snapshot, screeningMode);
  }); } catch (error) { if (!timedOut && isCurrent()) showRequestError(error); }
}
function injectControl(post) {
  if (post.closest('#suriph-control-host') || post.hasAttribute(CONTROL_ATTRIBUTE) || post.querySelector(':scope > #suriph-control-host')) return;
  post.setAttribute(CONTROL_ATTRIBUTE, 'true');
  if (window.getComputedStyle(post).position === 'static') post.style.position = 'relative';
  const host = document.createElement('div'); host.id = 'suriph-control-host'; host._suriphPost = post; host.setAttribute('aria-label', 'SuriPH post screening control'); positionControlHost(host);
  const shadow = host.attachShadow({ mode: 'open' });
  shadow.addEventListener('click', event => event.stopPropagation());
  const style = document.createElement('style');
  style.textContent = modalCss;
  const wrap = document.createElement('div'); wrap.className = 'wrap'; const button = document.createElement('button'); button.className = 'action'; button.type = 'button'; button.textContent = 'S'; button.dataset.recheck = 'false'; button.dataset.isOpen = 'false'; button.title = tr('Check with SuriPH', 'Suriin gamit ang SuriPH'); button.setAttribute('aria-label', tr('Check this post with SuriPH', 'Suriin gamit ang SuriPH')); const close = document.createElement('button'); close.type = 'button'; close.className = 'close'; close.textContent = '×'; close.title = tr('Close result', 'Isara ang resulta'); const message = document.createElement('div'); message.className = 'message'; message.hidden = true; const result = document.createElement('div'); result.className = 'message result'; result.hidden = true;
  close.addEventListener('click', (event) => {
    event.preventDefault(); event.stopPropagation();
    host.dataset.requestEpoch = String(Number(host.dataset.requestEpoch || 0) + 1);
    closeResultDialog(host);
    const hasCachedResult = Boolean(host._suriphResultCache);
    wrap.classList.remove('expanded');
    wrap.style.position = ''; wrap.style.display = ''; wrap.style.flexDirection = '';
    wrap.style.removeProperty('width'); wrap.style.removeProperty('max-width');
    wrap.style.removeProperty('max-height'); wrap.style.removeProperty('overflow-y');
    wrap.style.removeProperty('flex');
    wrap.style.removeProperty('background'); wrap.style.color = '';
    button.style.order = ''; button.style.marginTop = '';
    message.style.order = ''; message.style.color = ''; result.style.order = '';
    message.hidden = true; result.hidden = true;
    if (!hasCachedResult) {
      message.replaceChildren(); result.replaceChildren();
      button.dataset.recheck = 'false';
      delete button.dataset.previewConfirmed; delete button.dataset.resultPart; delete button.dataset.needsReload;
    }
    button.disabled = false; button.textContent = 'S'; button.dataset.isOpen = 'false';
    button.title = hasCachedResult
      ? tr('Show previous SuriPH result', 'Ipakita ang dating resulta ng SuriPH')
      : tr('Check with SuriPH', 'Suriin gamit ang SuriPH');
    button.setAttribute('aria-label', button.title);
    if (post.isConnected) post.appendChild(host);
    else { discardCachedResult(host); host.remove(); }
    positionControlHost(host);
    if (activeResultHost === host) activeResultHost = null;
    document.querySelectorAll('#suriph-control-host').forEach(other => { other.style.visibility = ''; });
  });
  button.addEventListener('click', () => {
    if (button.dataset.needsReload === 'true' || !extensionContextAvailable()) { location.reload(); return; }
    const cache = host._suriphResultCache;
    if (cache && button.dataset.isOpen !== 'true') {
      const currentSnapshot = {
        text: collectPostText(post),
        media: collectPostMedia(post),
        context: collectPostContext(post, 'Facebook post caption'),
        pageUrl: location.href,
        pageTitle: document.title,
      };
      if (post.isConnected && cache.key === postResultCacheKey(currentSnapshot, result.dataset.mediaChoice)) {
        showResult(host, button, message, result);
        return;
      }
      discardCachedResult(host);
    }
    analyzePost(post, button, message, result);
  });
  wrap.append(close, button, message, result); shadow.append(style, wrap); post.appendChild(host);
  const header = document.createElement('div'); header.className = 'modal-header';
  const brand = document.createElement('div'); brand.className = 'brand';
  const brandMark = document.createElement('span'); brandMark.className = 'brand-mark'; brandMark.appendChild(makeIcon('shield'));
  const brandName = document.createElement('span'); const name = document.createElement('strong'); name.textContent = 'SuriPH'; const subtitle = document.createElement('small'); subtitle.textContent = 'Post screening'; brandName.append(name, subtitle); brand.append(brandMark, brandName);
  const tools = document.createElement('div'); tools.className = 'modal-tools'; close.textContent = ''; close.appendChild(makeIcon('close')); close.setAttribute('aria-label', tr('Close result', 'Isara ang resulta')); tools.appendChild(close);
  header.append(brand, tools); wrap.prepend(header);
}
function scanForControls() { if (extensionEnabled) for (const post of findPosts()) injectControl(post); if (activeResultHost?.isConnected) document.querySelectorAll('#suriph-control-host').forEach(other => { if (other !== activeResultHost) other.style.visibility = 'hidden'; }); return document.querySelectorAll('#suriph-control-host').length; }
function removeControls() { document.querySelectorAll('#suriph-control-host').forEach((host) => host.remove()); document.querySelectorAll(`[${CONTROL_ATTRIBUTE}]`).forEach((post) => post.removeAttribute(CONTROL_ATTRIBUTE)); }
chrome.storage.local.get({ suriphEnabled: true, suriphRetrieveSources: true, suriphLanguage: 'en' }, (settings) => {
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
      const post = postForSelection();
      sendResponse(text ? { ok: true, text, mode: 'selection', context: post ? collectPostContext(post, 'Selected Facebook text') : { extraction_scope: 'Selected Facebook text' } } : { ok: false, error: tr('Select readable text on the page first.', 'Pumili muna ng mababasang teksto sa Facebook page.') });
      return false;
    }
    if (message.mode === 'post') {
      const post = postForSelection() || postNearestViewport();
      const text = post ? collectPostText(post) : '';
      const incomplete = captionLooksIncomplete(post, text);
      sendResponse(text && !incomplete ? { ok: true, text, mode: 'post', context: { ...collectPostContext(post, 'Facebook post caption'), caption_complete: true } } : { ok: false, error: incomplete ? tr('The caption looks incomplete. Expand See more or select the complete media.', 'Mukhang kulang ang caption. Buksan ang See more o piliin ang buong media.') : tr('No readable Facebook post or caption is visible.', 'Walang nakikitang mababasang Facebook post o caption.') });
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
  if (message?.type === 'SURIPH_RESCAN_CONTROLS') {
    sendResponse({ ok: true, controls: scanForControls() });
    return false;
  }
  return false;
});
new MutationObserver(scanForControls).observe(document.documentElement, { childList: true, subtree: true });
