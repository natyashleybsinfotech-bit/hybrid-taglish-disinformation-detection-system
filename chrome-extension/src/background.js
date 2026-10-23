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
async function boundedFetch(url, options = {}) {
  const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 120000);
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
async function postRelatedSources(payload) {
  let response;
  try { response = await boundedFetch(`${API_BASE}/related-sources`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: payload.text, page_url: payload.page_url || null }) }); }
  catch (_) { throw new Error('Evidence lookup is unavailable. No verdict was produced.'); }
  const body = await response.json().catch(() => ({})); if (!response.ok) throw new Error(body.detail || `Source lookup failed with status ${response.status}.`); return body;
}
async function postMedia(path, url, payload) {
  let mediaResponse;
  const parsed = new URL(url); const host = parsed.hostname.toLowerCase();
  if (parsed.protocol !== 'https:' || !['facebook.com','fbcdn.net','fbsbx.com'].some(domain => host === domain || host.endsWith(`.${domain}`))) throw new Error('This Facebook media origin is not supported. Use a local file through the popup.');
  try { mediaResponse = await boundedFetch(url); } catch (_) { throw new Error('Post media could not be fetched. The platform may be protecting or expiring this media URL.'); }
  if (!mediaResponse.ok) throw new Error(`Post media fetch failed (${mediaResponse.status}).`);
  const blob = await mediaResponse.blob(); if (!blob.size) throw new Error('The post media was empty.');
  if (blob.size > 50 * 1024 * 1024) throw new Error('Media exceeds the 50 MiB limit.');
  const form = new FormData(); form.append('file', blob, `suriph-${path.includes('video') ? 'post.mp4' : 'post.jpg'}`);
  if (path.includes('image')) form.append('capture_candidate', 'false');
  if (payload.page_url) form.append('page_url', payload.page_url); if (payload.page_title) form.append('page_title', payload.page_title);
  if (payload.text) form.append('post_text', payload.text); if (payload.context) form.append('context_json', JSON.stringify(payload.context));
  form.append('retrieve_sources', String(payload.retrieve_sources === true));
  let response;
  try { response = await boundedFetch(`${API_BASE}/${path}`, { method: 'POST', body: form }); }
  catch (_) { throw new Error('SuriPH backend is unavailable. Check the configured API connection.'); }
  const body = await response.json().catch(() => ({})); if (!response.ok) throw new Error(body.detail || `Media processing failed with status ${response.status}.`); return body;
}
async function postMediaBlob(path, blob, payload) {
  const form = new FormData(); form.append('file', blob, 'suriph-captured-video.webm');
  if (payload.page_url) form.append('page_url', payload.page_url); if (payload.page_title) form.append('page_title', payload.page_title);
  if (payload.text) form.append('post_text', payload.text); if (payload.context) form.append('context_json', JSON.stringify(payload.context));
  form.append('retrieve_sources', String(payload.retrieve_sources === true));
  const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 300000);
  let response; try { response = await fetch(`${API_BASE}/${path}`, { method: 'POST', body: form, signal: controller.signal }); } catch (error) { if (error.name === 'AbortError') throw new Error('Video processing timed out after 5 minutes. Try a shorter video or upload the file through the popup.'); throw error; } finally { clearTimeout(timeout); }
  const body = await response.json().catch(() => ({})); if (!response.ok) throw new Error(body.detail || `Media processing failed with status ${response.status}.`); return body;
}
async function analyzePayload(payload) {
  const media = payload.media || {};
  if (media.video_url || media.has_video) {
    if (!media.video_url) throw new Error('The selected video is unavailable. Choose caption/text explicitly to screen its caption.');
    return postMedia('analyze/video', media.video_url, payload);
  }
  if (Array.isArray(media.image_urls) && media.image_urls.length) {
    const extracted = [];
    for (const url of media.image_urls) {
      const result = await postMedia('analyze/image', url, payload);
      if (result.extraction?.ocr_text) extracted.push(result.extraction.ocr_text);
    }
    if (!extracted.length) throw new Error('No readable image text was extracted. No caption-only assessment was substituted.');
    return postJson({ text: `${payload.text || ''}\n${extracted.join('\n')}`.trim(), page_url: payload.page_url, page_title: payload.page_title, context: payload.context, retrieve_sources: payload.retrieve_sources === true });
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
  if (message?.type === 'SURIPH_ANALYZE_CAPTURE') {
    let bytes = null;
    try { if (message.videoBase64) { const binary = atob(message.videoBase64); bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0)); } } catch (_) { bytes = null; }
    if (!bytes?.length) { sendResponse({ ok: false, error: 'The in-page video capture was empty.' }); return false; }
    postMediaBlob('analyze/video', new Blob([bytes], { type: 'video/webm' }), message.payload || {})
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
