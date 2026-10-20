// Runs the actual extension API client and background handler against a live API.
// Chrome's message registration is simulated; fetch and inference are real.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const base = process.env.SURI_TEST_API_URL;
assert.ok(base?.startsWith('http://127.0.0.1:'), 'Supply an isolated local test API');
const apiSource = (await readFile(new URL('../src/api.js', import.meta.url), 'utf8'))
  .replaceAll('import.meta.env.VITE_API_BASE_URL', JSON.stringify(base));
const api = await import(`data:text/javascript;base64,${Buffer.from(apiSource).toString('base64')}`);
const text = `Integration request ${Date.now()}: Basahin muna ang buong balita at ang source nito.`;
const direct = await api.analyzeText({ text });
assert.equal(direct.training_run_id, '20261011T235112Z');
assert.equal(direct.analyzed_text, text);
assert.equal(direct.decision_threshold, .65);
assert.equal(direct.artifact_sha256, '72d87971ee2af7fca1f6f0a9b94bbe92618bd92ce8c5e48e35b80882e1321c7c');
assert.ok(Number.isFinite(direct.model_score));
assert.equal(direct.predicted_class, Number(direct.model_score >= .65));
await assert.rejects(api.analyzeText({ text: '   ' }));
let handler;
const calls = [];
const background = (await readFile(new URL('../src/background.js', import.meta.url), 'utf8'))
  .replaceAll('import.meta.env.VITE_API_BASE_URL', JSON.stringify(base));
vm.runInNewContext(background, {
  fetch: (...args) => { calls.push(String(args[0])); return fetch(...args); },
  chrome: { runtime: { onMessage: { addListener: callback => { handler = callback; } } } },
  FormData, Blob, AbortController, setTimeout, clearTimeout, Uint8Array, atob,
});
const response = await new Promise(resolve => handler({ type: 'SURIPH_ANALYZE_TEXT', payload: { text } }, {}, resolve));
assert.equal(response.ok, true);
assert.equal(response.result.analyzed_text, text);
assert.ok(Math.abs(response.result.model_score - direct.model_score) <= 1e-8);
assert.deepEqual(calls, [`${base}/analyze`]);
calls.length = 0;
const failedMedia = await new Promise(resolve => handler({ type: 'SURIPH_ANALYZE_TEXT', payload: { text, media: { has_video: true } } }, {}, resolve));
assert.equal(failedMedia.ok, false);
assert.equal(calls.length, 0, 'Unavailable video must not silently produce a caption-only result');
console.log(JSON.stringify({ extension_api_client: 'passed', background_transport: 'passed', media_failure_no_substitution: 'passed', browser_ui_tested: false }));
