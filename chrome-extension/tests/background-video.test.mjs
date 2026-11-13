import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

const source = readFileSync(new URL('../src/background.js', import.meta.url), 'utf8')
  .replaceAll('import.meta.env', '({})');

function startVideoRequest(videoUrl, fetchImpl) {
  let onConnect;
  const chrome = {
    runtime: {
      onInstalled: { addListener() {} },
      onConnect: { addListener(listener) { onConnect = listener; } },
      onMessage: { addListener() {} },
    },
    storage: { local: { get() {}, set() {} } },
  };
  runInNewContext(source, { chrome, fetch: fetchImpl, Blob, FormData, URL,
    Uint8Array, AbortController, setTimeout, clearTimeout, atob });
  let onMessage;
  let resolveResult;
  const result = new Promise(resolve => { resolveResult = resolve; });
  onConnect({
    name: 'SURIPH_VIDEO_ANALYSIS',
    onDisconnect: { addListener() {} },
    onMessage: { addListener(listener) { onMessage = listener; } },
    postMessage(value) { resolveResult(value); },
  });
  onMessage({ type: 'ANALYZE_VIDEO', videoUrl,
    payload: { text: 'Exact selected caption', page_url: 'https://www.facebook.com/reel/123', retrieve_sources: true } });
  return result;
}

test('background direct video fetch uploads the selected media and caption without recording playback', async () => {
  const requested = [];
  const result = await startVideoRequest('https://cdn.fbcdn.net/selected.mp4', async (url, options) => {
    requested.push({ url, options });
    if (url.startsWith('https://')) return new Response(new Blob(['video bytes'], { type: 'video/mp4' }));
    const form = options.body;
    assert.equal(form.get('post_text'), 'Exact selected caption');
    assert.equal(form.get('page_url'), 'https://www.facebook.com/reel/123');
    assert.equal(form.get('retrieve_sources'), 'true');
    assert.equal(form.get('file').type, 'video/mp4');
    return new Response(JSON.stringify({ review_required: true, extraction: { transcript_text: 'sample' } }),
      { status: 200, headers: { 'Content-Type': 'application/json' } });
  });
  assert.equal(result.ok, true);
  assert.equal(result.result.review_required, true);
  assert.deepEqual(requested.map(item => item.url), [
    'https://cdn.fbcdn.net/selected.mp4', 'http://127.0.0.1:8000/analyze/video',
  ]);
  assert.equal(requested[0].options.credentials, 'include');
});

test('unavailable direct video URL explicitly permits complete capture fallback', async () => {
  const requested = [];
  const result = await startVideoRequest('https://cdn.fbcdn.net/expired.mp4', async url => {
    requested.push(url);
    throw new TypeError('Expired media URL');
  });
  assert.equal(result.ok, false);
  assert.equal(result.fallback_to_capture, true);
  assert.deepEqual(requested, ['https://cdn.fbcdn.net/expired.mp4']);
});

test('partial video response falls back instead of transcribing an incomplete clip', async () => {
  const requested = [];
  const result = await startVideoRequest('https://cdn.fbcdn.net/partial.mp4', async url => {
    requested.push(url);
    return new Response(new Blob(['partial'], { type: 'video/mp4' }), { status: 206 });
  });
  assert.equal(result.ok, false);
  assert.equal(result.fallback_to_capture, true);
  assert.deepEqual(requested, ['https://cdn.fbcdn.net/partial.mp4']);
});

test('backend extraction failure after a successful download does not repeat video capture', async () => {
  const requested = [];
  const result = await startVideoRequest('https://cdn.fbcdn.net/selected.mp4', async url => {
    requested.push(url);
    if (url.startsWith('https://')) return new Response(new Blob(['video bytes'], { type: 'video/mp4' }));
    return new Response(JSON.stringify({ detail: 'Speech quality is insufficient.' }),
      { status: 422, headers: { 'Content-Type': 'application/json' } });
  });
  assert.equal(result.ok, false);
  assert.equal(result.fallback_to_capture, false);
  assert.deepEqual(requested, [
    'https://cdn.fbcdn.net/selected.mp4', 'http://127.0.0.1:8000/analyze/video',
  ]);
});

test('a downloaded Facebook video without decodable audio permits playback capture', async () => {
  const requested = [];
  const result = await startVideoRequest('https://cdn.fbcdn.net/video-only.mp4', async url => {
    requested.push(url);
    if (url.startsWith('https://')) return new Response(new Blob(['video bytes'], { type: 'video/mp4' }));
    return new Response(JSON.stringify({ detail: 'FFmpeg could not process the submitted video.' }),
      { status: 422, headers: { 'Content-Type': 'application/json' } });
  });
  assert.equal(result.ok, false);
  assert.equal(result.fallback_to_capture, true);
  assert.deepEqual(requested, [
    'https://cdn.fbcdn.net/video-only.mp4', 'http://127.0.0.1:8000/analyze/video',
  ]);
});
