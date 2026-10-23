const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const REQUEST_TIMEOUT_MS = Number(import.meta.env?.VITE_REQUEST_TIMEOUT_MS || 120_000);

async function request(path, options) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(`${API_BASE}${path}`, { ...options, signal: controller.signal });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = Array.isArray(body.detail) ? body.detail.map(item => item.msg).join(' ') : body.detail;
      throw new Error(detail || `Request failed with status ${response.status}.`);
    }
    return body;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('The screening request timed out.');
    if (error.name === 'TypeError') throw new Error('The screening service is unavailable. Check the backend connection and try again.');
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export function analyzeText({ text, pageUrl, pageTitle, context = null, retrieveSources = false }) {
  return request('/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, page_url: pageUrl || null, page_title: pageTitle || null, context, retrieve_sources: retrieveSources }),
  });
}

export function lookupRelatedSources({ text, pageUrl }) {
  return request('/related-sources', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, page_url: pageUrl || null }),
  });
}

export function analyzeMedia(kind, file, page = {}) {
  const form = new FormData();
  form.append('file', file);
  if (page.url) form.append('page_url', page.url);
  if (page.title) form.append('page_title', page.title);
  if (page.postText) form.append('post_text', page.postText);
  if (page.context) form.append('context_json', JSON.stringify(page.context));
  form.append('retrieve_sources', String(page.retrieveSources || false));
  return request(`/analyze/${kind}`, { method: 'POST', body: form });
}
