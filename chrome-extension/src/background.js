const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const SOURCE_DEFAULT_VERSION = 1;
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.get({ suriphSourceDefaultVersion: 0 }, saved => {
    if (saved.suriphSourceDefaultVersion >= SOURCE_DEFAULT_VERSION) return;
    chrome.storage.local.set({
      suriphRetrieveSources: true,
      suriphSourceDefaultVersion: SOURCE_DEFAULT_VERSION,
    });
  });
});
chrome.runtime.onConnect.addListener(port => {
  if (port.name !== 'SURIPH_VIDEO_ANALYSIS') return;
  let started = false;
  let connected = true;
  port.onDisconnect.addListener(() => { connected = false; });
  port.onMessage.addListener(message => {
    if (message?.type === 'PING' || started || message?.type !== 'ANALYZE_VIDEO') return;
    started = true;
    if (message.videoUrl) {
      postMedia('analyze/video', message.videoUrl, message.payload || {})
        .then(result => { if (connected) port.postMessage({ ok: true, result }); })
        .catch(error => { if (connected) port.postMessage({ ok: false,
          fallback_to_capture: error.fallback_to_capture === true,
          error: error.message || 'Video analysis failed.' }); });
      return;
    }
    let bytes = null;
    try {
      if (message.videoBase64) {
        const binary = atob(message.videoBase64);
        bytes = Uint8Array.from(binary, character => character.charCodeAt(0));
      }
    } catch { bytes = null; }
    if (!bytes?.length) {
      port.postMessage({ ok: false, error: 'The in-page video capture was empty.' });
      return;
    }
    postMediaBlob('analyze/video', new Blob([bytes], { type: 'video/webm' }), message.payload || {})
      .then(result => { if (connected) port.postMessage({ ok: true, result }); })
      .catch(error => { if (connected) port.postMessage({ ok: false, error: error.message || 'Video analysis failed.' }); });
  });
});
async function boundedFetch(url, options = {}, timeoutMs = 120000) {
  const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), timeoutMs);
  try { return await fetch(url, { ...options, signal: controller.signal }); }
  catch (error) { if (error.name === 'AbortError') throw new Error('The request timed out. Try again with a shorter input.'); throw error; }
  finally { clearTimeout(timer); }
}
async function postJson(payload) {
  let response;
  try { response = await boundedFetch(`${API_BASE}/analyze`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); }
  catch (_) { throw new Error('SuriPH backend is unavailable. Check the configured API connection.'); }
  const body = await response.json().catch(() => ({})); if (!response.ok) throw new Error(body.detail || `Screening failed with status ${response.status}.`); return body;
}
async function confirmVideo(payload) {
  const response = await boundedFetch(`${API_BASE}/analyze/confirmed-video`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Video confirmation failed with status ${response.status}.`);
  return body;
}
async function postRelatedSources(payload) {
  let response;
  try { response = await boundedFetch(`${API_BASE}/related-sources`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: payload.text, page_url: payload.page_url || null }) }); }
  catch (_) { throw new Error('Related-source lookup is unavailable. The prediction is unchanged.'); }
  const body = await response.json().catch(() => ({})); if (!response.ok) throw new Error(body.detail || `Source lookup failed with status ${response.status}.`); return body;
}
async function postMedia(path, url, payload) {
  let mediaResponse;
  const parsed = new URL(url); const host = parsed.hostname.toLowerCase();
  const fetchFailure = message => Object.assign(new Error(message), { fallback_to_capture: true });
  if (parsed.protocol !== 'https:' || !['facebook.com','fbcdn.net','fbsbx.com'].some(domain => host === domain || host.endsWith(`.${domain}`))) throw fetchFailure('This Facebook media origin is not supported. Use a local file through the popup.');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), path.includes('video') ? 30000 : 120000);
  let blob;
  try {
    mediaResponse = await fetch(url, { credentials: 'include', signal: controller.signal });
    if (!mediaResponse.ok) throw fetchFailure(`Post media fetch failed (${mediaResponse.status}).`);
    if (path.includes('video') && mediaResponse.status !== 200) throw fetchFailure('The media server returned only part of the video.');
    blob = await mediaResponse.blob();
    if (!blob.size) throw fetchFailure('The post media was empty.');
  } catch (error) {
    if (error.fallback_to_capture) throw error;
    throw fetchFailure('Post media could not be fetched. The platform may be protecting or expiring this media URL.');
  } finally { clearTimeout(timer); }
  if (blob.size > 50 * 1024 * 1024) throw new Error('Media exceeds the 50 MiB limit.');
  if (path.includes('video') && !blob.type.startsWith('video/')) {
    const head = new Uint8Array(await blob.slice(0, 12).arrayBuffer());
    const mp4 = head.length >= 8 && String.fromCharCode(...head.slice(4, 8)) === 'ftyp';
    const webm = head.length >= 4 && head[0] === 0x1a && head[1] === 0x45 && head[2] === 0xdf && head[3] === 0xa3;
    if (!mp4 && !webm) throw fetchFailure('The media URL did not return a playable video file.');
    blob = new Blob([blob], { type: mp4 ? 'video/mp4' : 'video/webm' });
  }
  const form = new FormData(); form.append('file', blob, `suriph-${path.includes('video') ? (blob.type === 'video/webm' ? 'post.webm' : 'post.mp4') : 'post.jpg'}`);
  if (path.includes('image')) form.append('capture_candidate', 'false');
  if (payload.page_url) form.append('page_url', payload.page_url); if (payload.page_title) form.append('page_title', payload.page_title);
  if (payload.text) form.append('post_text', payload.text); if (payload.context) form.append('context_json', JSON.stringify(payload.context));
  form.append('retrieve_sources', String(payload.retrieve_sources === true));
  let response;
  try { response = await boundedFetch(`${API_BASE}/${path}`, { method: 'POST', body: form }, path.includes('video') ? 420000 : 120000); }
  catch (_) { throw new Error('SuriPH backend is unavailable. Check the configured API connection.'); }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body.detail || `Media processing failed with status ${response.status}.`);
    // Facebook may expose a video-only stream while audio plays separately.
    // In that narrow case, capture the selected playback with its audio track.
    if (path.includes('video') && response.status === 422 &&
        ['FFmpeg could not process the submitted video.', 'The extracted audio could not be decoded.'].includes(error.message)) {
      error.fallback_to_capture = true;
    }
    throw error;
  }
  return body;
}
async function postMediaBlob(path, blob, payload) {
  const form = new FormData(); form.append('file', blob, 'suriph-captured-video.webm');
  if (payload.page_url) form.append('page_url', payload.page_url); if (payload.page_title) form.append('page_title', payload.page_title);
  if (payload.text) form.append('post_text', payload.text); if (payload.context) form.append('context_json', JSON.stringify(payload.context));
  form.append('retrieve_sources', String(payload.retrieve_sources === true));
  const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 420000);
  let response; try { response = await fetch(`${API_BASE}/${path}`, { method: 'POST', body: form, signal: controller.signal }); } catch (error) { if (error.name === 'AbortError') throw new Error('Video processing timed out after 7 minutes. Try a shorter video or upload the file through the popup.'); throw error; } finally { clearTimeout(timeout); }
  const body = await response.json().catch(() => ({})); if (!response.ok) throw new Error(body.detail || `Media processing failed with status ${response.status}.`); return body;
}
async function postImages(urls, payload) {
  if (!Array.isArray(urls) || urls.length < 2 || urls.length > 4) throw new Error('Select between two and four images from the same post.');
  const form = new FormData();
  let totalBytes = 0;
  for (const [index, value] of urls.entries()) {
    const parsed = new URL(value); const host = parsed.hostname.toLowerCase();
    if (parsed.protocol !== 'https:' || !['facebook.com', 'fbcdn.net', 'fbsbx.com'].some(domain => host === domain || host.endsWith(`.${domain}`)))
      throw new Error('This Facebook image origin is not supported. Use a local file through the popup.');
    let response;
    try { response = await boundedFetch(parsed.href); }
    catch { throw new Error(`Image ${index + 1} could not be fetched. No prediction was made.`); }
    if (!response.ok) throw new Error(`Image ${index + 1} could not be fetched (${response.status}). No prediction was made.`);
    const blob = await response.blob(); totalBytes += blob.size;
    if (!blob.size || totalBytes > 50 * 1024 * 1024) throw new Error('The selected images are empty or exceed the 50 MiB limit. No prediction was made.');
    form.append('files', blob.type.startsWith('image/') ? blob : new Blob([blob], { type: 'image/jpeg' }), `suriph-post-image-${index + 1}.jpg`);
  }
  if (payload.page_url) form.append('page_url', payload.page_url);
  if (payload.page_title) form.append('page_title', payload.page_title);
  if (payload.text) form.append('post_text', payload.text);
  if (payload.context) form.append('context_json', JSON.stringify(payload.context));
  form.append('retrieve_sources', String(payload.retrieve_sources === true));
  let response;
  try { response = await boundedFetch(`${API_BASE}/analyze/images`, { method: 'POST', body: form }, 420000); }
  catch { throw new Error('SuriPH backend is unavailable or image processing timed out. No prediction was made.'); }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Image processing failed with status ${response.status}.`);
  return body;
}
async function analyzePayload(payload) {
  const media = payload.media || {};
  if (media.video_url || media.has_video) {
    if (!media.video_url) throw new Error('The selected video is unavailable. Choose caption/text explicitly to screen its caption.');
    return postMedia('extract/video', media.video_url, payload);
  }
  if (Array.isArray(media.image_urls) && media.image_urls.length) {
    if (media.image_urls.length === 1) return postMedia('analyze/image', media.image_urls[0], payload);
    return postImages(media.image_urls, payload);
  }
  return postJson(payload);
}
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === 'SURIPH_LOOKUP_SOURCES') {
    postRelatedSources(message.payload || {})
      .then((body) => sendResponse({ ok: true, result: body }))
      .catch((error) => sendResponse({ ok: false, error: error.message || 'Related-source lookup failed.' }));
    return true;
  }
  if (message?.type === 'SURIPH_CONFIRM_VIDEO') {
    confirmVideo(message.payload || {})
      .then((body) => sendResponse({ ok: true, result: body }))
      .catch((error) => sendResponse({ ok: false, error: error.message || 'Video confirmation failed.' }));
    return true;
  }
  if (message?.type === 'SURIPH_EXTRACT_CAPTURE') {
    let bytes = null;
    try { if (message.videoBase64) { const binary = atob(message.videoBase64); bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0)); } } catch (_) { bytes = null; }
    if (!bytes?.length) { sendResponse({ ok: false, error: 'The in-page video capture was empty.' }); return false; }
    postMediaBlob('extract/video', new Blob([bytes], { type: 'video/webm' }), message.payload || {})
      .then((body) => sendResponse({ ok: true, result: body }))
      .catch((error) => sendResponse({ ok: false, error: error.message || 'Captured video processing failed.' }));
    return true;
  }
  if (message?.type !== 'SURIPH_ANALYZE_TEXT') return false;
  analyzePayload(message.payload)
    .then((body) => { sendResponse({ ok: true, result: body }); })
    .catch((error) => sendResponse({ ok: false, error: error.message || 'SuriPH backend is unavailable.' }));
  return true;
});
