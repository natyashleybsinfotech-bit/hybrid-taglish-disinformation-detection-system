const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const REQUEST_TIMEOUT_MS = 120_000;

async function request(path, options) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(`${API_BASE}${path}`, { ...options, signal: controller.signal });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(body.detail || `Request failed with status ${response.status}.`);
    }
    return body;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('The screening request timed out.');
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export function analyzeText({ text, pageUrl, pageTitle }) {
  return request('/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, page_url: pageUrl || null, page_title: pageTitle || null }),
  });
}

export function analyzeMedia(kind, file, page = {}) {
  const form = new FormData();
  form.append('file', file);
  if (page.url) form.append('page_url', page.url);
  if (page.title) form.append('page_title', page.title);
  return request(`/analyze/${kind}`, { method: 'POST', body: form });
}

export function submitCandidate({ text, pageUrl, pageTitle }) {
  return request('/candidates', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, page_url: pageUrl || null, page_title: pageTitle || null }),
  });
}
