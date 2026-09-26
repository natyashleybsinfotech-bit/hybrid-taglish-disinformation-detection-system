const API_BASE = 'http://127.0.0.1:8000';
async function postJson(payload) {
  let response;
  try { response = await fetch(`${API_BASE}/analyze`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); }
  catch (_) { throw new Error('SuriPH backend is unavailable. Start the FastAPI server on 127.0.0.1:8000.'); }
  const body = await response.json().catch(() => ({})); if (!response.ok) throw new Error(body.detail || `Screening failed with status ${response.status}.`); return body;
}
async function postMedia(path, url, payload) {
  let mediaResponse;
  try { mediaResponse = await fetch(url); } catch (_) { throw new Error('Post media could not be fetched. The platform may be protecting or expiring this media URL.'); }
  if (!mediaResponse.ok) throw new Error(`Post media fetch failed (${mediaResponse.status}).`);
  const blob = await mediaResponse.blob(); if (!blob.size) throw new Error('The post media was empty.');
  const form = new FormData(); form.append('file', blob, `suriph-${path.includes('video') ? 'post.mp4' : 'post.jpg'}`);
  if (payload.page_url) form.append('page_url', payload.page_url); if (payload.page_title) form.append('page_title', payload.page_title);
  if (payload.text) form.append('post_text', payload.text); if (payload.context) form.append('context_json', JSON.stringify(payload.context));
  let response;
  try { response = await fetch(`${API_BASE}/${path}`, { method: 'POST', body: form }); }
  catch (_) { throw new Error('SuriPH backend is unavailable. Start the FastAPI server on 127.0.0.1:8000.'); }
  const body = await response.json().catch(() => ({})); if (!response.ok) throw new Error(body.detail || `Media processing failed with status ${response.status}.`); return body;
}
async function postMediaBlob(path, blob, payload) {
  const form = new FormData(); form.append('file', blob, 'suriph-captured-video.webm');
  if (payload.page_url) form.append('page_url', payload.page_url); if (payload.page_title) form.append('page_title', payload.page_title);
  if (payload.text) form.append('post_text', payload.text); if (payload.context) form.append('context_json', JSON.stringify(payload.context));
  const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 300000);
  let response; try { response = await fetch(`${API_BASE}/${path}`, { method: 'POST', body: form, signal: controller.signal }); } catch (error) { if (error.name === 'AbortError') throw new Error('Video processing timed out after 5 minutes. Try a shorter video or upload the file through the popup.'); throw error; } finally { clearTimeout(timeout); }
  const body = await response.json().catch(() => ({})); if (!response.ok) throw new Error(body.detail || `Media processing failed with status ${response.status}.`); return body;
}
async function analyzePayload(payload) {
  const media = payload.media || {};
  if (media.video_url || media.has_video) {
    if (!media.video_url) { if (!payload.text?.trim()) throw new Error('This video is protected by the platform and could not be fetched for processing.'); const result = await postJson(payload); result.media_status = 'unavailable'; result.media_error = 'The video URL was not accessible; caption screening is shown.'; return result; }
    try { const result = await postMedia('analyze/video', media.video_url, payload); result.context = payload.context || {}; return result; }
    catch (error) { if (!payload.text?.trim()) throw error; const result = await postJson(payload); result.media_status = 'unavailable'; result.media_error = error.message; return result; }
  }
  if (Array.isArray(media.image_urls) && media.image_urls.length) {
    const extracted = [];
    for (const url of media.image_urls) { try { const result = await postMedia('analyze/image', url, payload); if (result.extraction?.ocr_text) extracted.push(result.extraction.ocr_text); } catch (_) { /* keep other images usable */ } }
    if (extracted.length) return postJson({ text: `${payload.text || ''}\n${extracted.join('\n')}`.trim(), page_url: payload.page_url, page_title: payload.page_title, context: payload.context });
  }
  return postJson(payload);
}
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
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
