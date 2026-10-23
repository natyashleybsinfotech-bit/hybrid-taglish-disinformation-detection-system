// Runs the actual extension API client and background handler against one live local API.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const base = process.env.SURI_TEST_API_URL;
assert.ok(base?.startsWith('http://127.0.0.1:'), 'Supply an isolated local test API');
const health = await fetch(`${base}/health`).then(response => response.json());
assert.equal(health.decision_engine.mode, 'evidence_only');
assert.equal(health.decision_engine.classifier_loaded, false);
assert.equal(health.model.status, 'disabled');

const apiSource = (await readFile(new URL('../src/api.js', import.meta.url), 'utf8')).replaceAll('import.meta.env.VITE_API_BASE_URL', JSON.stringify(base));
const api = await import(`data:text/javascript;base64,${Buffer.from(apiSource).toString('base64')}`);
const text = `Evidence integration request ${Date.now()}: Basahin ang buong balita at ang source nito.`;
const direct = await api.analyzeText({ text, retrieveSources: false });
assert.equal(direct.analyzed_text, text);
assert.equal(direct.decision_mode, 'evidence_only');
assert.equal(direct.classification_performed, false);
assert.equal(direct.classifier_loaded, false);
assert.equal(direct.assessment_status, 'unresolved');
for (const forbidden of ['model_score', 'confidence', 'predicted_class', 'internal_label', 'public_label', 'decision_threshold']) assert.equal(forbidden in direct, false);
await assert.rejects(api.analyzeText({ text: '   ' }));

let handler;
let installedHandler;
const storedSettings = {};
const calls = [];
const background = (await readFile(new URL('../src/background.js', import.meta.url), 'utf8')).replaceAll('import.meta.env.VITE_API_BASE_URL', JSON.stringify(base));
vm.runInNewContext(background, {
  fetch: (...args) => { calls.push(String(args[0])); return fetch(...args); },
  chrome: {
    runtime: { onInstalled: { addListener: callback => { installedHandler = callback; } }, onMessage: { addListener: callback => { handler = callback; } } },
    storage: { local: { get: (defaults, callback) => callback({ ...defaults, ...storedSettings }), set: values => Object.assign(storedSettings, values) } },
  },
  FormData, Blob, AbortController, setTimeout, clearTimeout, Uint8Array, atob,
});
installedHandler({ reason: 'update' });
assert.equal(storedSettings.suriphRetrieveSources, true);
const response = await new Promise(resolve => handler({ type: 'SURIPH_ANALYZE_TEXT', payload: { text, retrieve_sources: false } }, {}, resolve));
assert.equal(response.ok, true);
assert.equal(response.result.analyzed_text, text);
assert.equal(response.result.classification_performed, false);
assert.deepEqual(calls, [`${base}/analyze`]);
calls.length = 0;
const sourceResponse = await new Promise(resolve => handler({ type: 'SURIPH_LOOKUP_SOURCES', payload: { text, page_url: 'https://www.facebook.com/example/posts/1' } }, {}, resolve));
assert.equal(sourceResponse.ok, true);
assert.equal(sourceResponse.result.classification_performed, false);
assert.equal('model_score' in sourceResponse.result, false);
assert.deepEqual(calls, [`${base}/related-sources`]);

console.log(JSON.stringify({ extension_api_client: 'passed', evidence_only_transport: 'passed', no_classifier_fields: 'passed', browser_ui_tested: false }));
