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
const directSources = await api.lookupRelatedSources({ text, pageUrl: 'https://www.facebook.com/example/posts/1' });
assert.equal(directSources.classification_performed, false);
assert.ok(['available', 'no_results', 'unavailable'].includes(directSources.retrieval_status));
assert.equal('model_score' in directSources, false, 'Source-only lookup must not return a replacement prediction');
await assert.rejects(api.analyzeText({ text: '   ' }));
const unavailableSource = apiSource.replaceAll(base, 'http://127.0.0.1:9');
const unavailableApi = await import(`data:text/javascript;base64,${Buffer.from(unavailableSource).toString('base64')}`);
await assert.rejects(unavailableApi.analyzeText({ text }), /screening service is unavailable/i);
let handler;
let installedHandler;
const storedSettings = {};
const calls = [];
const background = (await readFile(new URL('../src/background.js', import.meta.url), 'utf8'))
  .replaceAll('import.meta.env.VITE_API_BASE_URL', JSON.stringify(base));
vm.runInNewContext(background, {
  fetch: (...args) => { calls.push(String(args[0])); return fetch(...args); },
  chrome: {
    runtime: {
      onInstalled: { addListener: callback => { installedHandler = callback; } },
      onMessage: { addListener: callback => { handler = callback; } },
    },
    storage: {
      local: {
        get: (defaults, callback) => callback({ ...defaults, ...storedSettings }),
        set: values => Object.assign(storedSettings, values),
      },
    },
  },
  FormData, Blob, AbortController, setTimeout, clearTimeout, Uint8Array, atob,
});
assert.equal(typeof installedHandler, 'function');
installedHandler({ reason: 'update' });
assert.equal(storedSettings.suriphRetrieveSources, true);
assert.equal(storedSettings.suriphSourceDefaultVersion, 1);
storedSettings.suriphRetrieveSources = false;
installedHandler({ reason: 'update' });
assert.equal(storedSettings.suriphRetrieveSources, false, 'A later browser restart/update must preserve the user choice');
const response = await new Promise(resolve => handler({ type: 'SURIPH_ANALYZE_TEXT', payload: { text } }, {}, resolve));
assert.equal(response.ok, true);
assert.equal(response.result.analyzed_text, text);
assert.ok(Math.abs(response.result.model_score - direct.model_score) <= 1e-8);
assert.deepEqual(calls, [`${base}/analyze`]);
calls.length = 0;
const sourceResponse = await new Promise(resolve => handler({ type: 'SURIPH_LOOKUP_SOURCES', payload: { text, page_url: 'https://www.facebook.com/example/posts/1' } }, {}, resolve));
assert.equal(sourceResponse.ok, true);
assert.equal(sourceResponse.result.classification_performed, false);
assert.equal('model_score' in sourceResponse.result, false);
assert.deepEqual(calls, [`${base}/related-sources`]);
calls.length = 0;
const failedMedia = await new Promise(resolve => handler({ type: 'SURIPH_ANALYZE_TEXT', payload: { text, media: { has_video: true } } }, {}, resolve));
assert.equal(failedMedia.ok, false);
assert.equal(calls.length, 0, 'Unavailable video must not silently produce a caption-only result');
console.log(JSON.stringify({ extension_api_client: 'passed', source_lookup_update_migration: 'passed', background_transport: 'passed', source_only_lookup_without_classification: 'passed', media_failure_no_substitution: 'passed', browser_ui_tested: false }));
