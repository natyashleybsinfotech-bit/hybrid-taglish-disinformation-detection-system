// Exercise the unpacked extension's real action popup against the running API.
// The Chrome profile and screenshots remain under ignored tmp/.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { spawn, spawnSync } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const CHROME = process.env.SURI_TEST_BROWSER || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const EXTENSION = path.join(ROOT, 'chrome-extension', 'dist');
const RUN = path.join(ROOT, 'tmp', `extension-popup-${Date.now()}`);
const PROFILE = path.join(RUN, 'profile');
const SHOTS = path.join(RUN, 'screenshots');
await Promise.all([mkdir(PROFILE, { recursive: true }), mkdir(SHOTS, { recursive: true })]);
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const displayPercent = value => value > .99995 && value < 1 ? '>99.99%' : value > 0 && value < .00005 ? '<0.01%' : `${(value * 100).toFixed(2)}%`;
const keepAlive = setInterval(() => {}, 1000);
const failureMode = process.env.SURI_EXPECT_UNAVAILABLE === '1';

class CDP {
  constructor(url) { this.url = url; this.id = 0; this.pending = new Map(); this.listeners = []; }
  async open() {
    this.socket = new WebSocket(this.url);
    await new Promise((resolve, reject) => { this.socket.onopen = resolve; this.socket.onerror = reject; });
    this.socket.onmessage = event => {
      const message = JSON.parse(event.data);
      for (const listener of this.listeners) listener(message);
      if (!message.id || !this.pending.has(message.id)) return;
      const pending = this.pending.get(message.id); this.pending.delete(message.id);
      message.error ? pending.reject(new Error(message.error.message)) : pending.resolve(message.result || {});
    };
    return this;
  }
  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((resolve, reject) => { this.pending.set(id, { resolve, reject }); this.socket.send(JSON.stringify({ id, method, params })); });
  }
  close() { this.socket?.close(); }
}

async function targets(port) { return fetch(`http://127.0.0.1:${port}/json/list`).then(response => response.json()); }
async function evaluate(client, expression, awaitPromise = false) {
  const output = await client.send('Runtime.evaluate', { expression, awaitPromise, returnByValue: true, userGesture: true });
  if (output.exceptionDetails) throw new Error(output.exceptionDetails.exception?.description || output.exceptionDetails.text);
  return output.result?.value;
}
async function waitFor(client, expression, timeout = 120000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) { try { if (await evaluate(client, expression, true)) return; } catch {} await wait(100); }
  throw new Error(`Timed out waiting for ${expression}`);
}
async function setValue(client, selector, value) {
  await evaluate(client, `(() => { const element=document.querySelector(${JSON.stringify(selector)}); const proto=element instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype; Object.getOwnPropertyDescriptor(proto,'value').set.call(element,${JSON.stringify(value)}); element.dispatchEvent(new Event('input',{bubbles:true})); element.dispatchEvent(new Event('change',{bubbles:true})); return true; })()`);
}
async function clickText(client, label) {
  await evaluate(client, `(() => { const node=[...document.querySelectorAll('button,summary')].find(item=>item.textContent.includes(${JSON.stringify(label)})); if(!node) throw new Error('Missing control'); node.click(); return true; })()`);
}
async function screenshot(client, name) {
  const result = await client.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  await writeFile(path.join(SHOTS, `${name}.png`), Buffer.from(result.data, 'base64'));
}

const chrome = spawn(CHROME, [
  '--disable-gpu', '--no-sandbox', '--no-first-run', '--no-default-browser-check', '--window-position=-32000,-32000', '--window-size=500,500',
  `--user-data-dir=${PROFILE}`, '--remote-debugging-port=0',
  `--disable-extensions-except=${EXTENSION}`, `--load-extension=${EXTENSION}`, 'about:blank',
], { windowsHide: true, stdio: 'ignore' });
let popup;
try {
  let port;
  for (let attempt = 0; attempt < 200 && !port; attempt++) {
    try { port = Number((await readFile(path.join(PROFILE, 'DevToolsActivePort'), 'utf8')).split(/\r?\n/)[0]); } catch { await wait(100); }
  }
  assert.ok(port, 'Chrome remote debugging did not start');
  let workerTarget;
  for (let attempt = 0; attempt < 100 && !workerTarget; attempt++) {
    workerTarget = (await targets(port)).find(item => item.type === 'service_worker' && item.url.endsWith('/service-worker-loader.js'));
    await wait(100);
  }
  if (!workerTarget) console.error(JSON.stringify((await targets(port)).map(item => ({ type: item.type, url: item.url }))));
  assert.ok(workerTarget, 'Unpacked extension service worker did not register');
  const extensionId = new URL(workerTarget.url).hostname;
  let popupTarget;
  let actionAvailable = false;
  if (failureMode) {
    popupTarget = await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(`chrome-extension://${extensionId}/index.html`)}`, { method: 'PUT' }).then(response => response.json());
  } else {
    const worker = await new CDP(workerTarget.webSocketDebuggerUrl).open();
    let workerContext;
    const workerContexts = [];
    worker.listeners.push(message => {
      if (message.method === 'Runtime.executionContextCreated') {
        workerContexts.push({ id: message.params.context.id, origin: message.params.context.origin, name: message.params.context.name });
        if (message.params.context.origin.startsWith(`chrome-extension://${extensionId}`)) workerContext = message.params.context.id;
      }
    });
    await worker.send('Runtime.enable');
    for (let attempt = 0; attempt < 50 && !workerContext; attempt++) await wait(100);
    assert.ok(workerContext, `Extension worker execution context was unavailable: ${JSON.stringify(workerContexts)}`);
    const workerEvaluate = async (expression, awaitPromise = false) => {
      const output = await worker.send('Runtime.evaluate', { expression, contextId: workerContext, awaitPromise, returnByValue: true, userGesture: true });
      if (output.exceptionDetails) throw new Error(output.exceptionDetails.exception?.description || output.exceptionDetails.text);
      return output.result?.value;
    };
    actionAvailable = await workerEvaluate('Boolean(chrome.action?.openPopup)');
    if (actionAvailable) await workerEvaluate('chrome.action.openPopup().then(()=>true)', true);
    else await workerEvaluate(`chrome.windows.create({url:chrome.runtime.getURL('index.html'),type:'popup',width:420,height:900}).then(()=>true)`, true);
    worker.close();
    for (let attempt = 0; attempt < 100 && !popupTarget; attempt++) {
      popupTarget = (await targets(port)).find(item => item.type === 'page' && item.url === `chrome-extension://${extensionId}/index.html`);
      await wait(100);
    }
  }
  assert.ok(popupTarget, 'Extension action popup did not open');
  popup = await new CDP(popupTarget.webSocketDebuggerUrl).open();
  await wait(1000);
  if (process.env.SURI_CDP_DEBUG === '1') console.error(await evaluate(popup, 'JSON.stringify({url:location.href,html:document.body?.innerHTML?.slice(0,500)})'));
  await waitFor(popup, 'Boolean(document.querySelector("#screen-text"))', 10000);
  if (failureMode) {
    await setValue(popup, '#screen-text', 'Synthetic disconnected-backend rehearsal.');
    await clickText(popup, 'Analyze text');
    await waitFor(popup, 'Boolean(document.querySelector("[role=alert]"))', 15000);
    assert.match(await evaluate(popup, 'document.querySelector("[role=alert]").textContent'), /service is unavailable/i);

    const actualFixture = JSON.parse((await readFile(path.join(ROOT, 'tmp', 'ui-real-result.json'), 'utf8')).replace(/^\uFEFF/, ''));
    for (const [retrievalStatus, expectedText] of [
      ['no_results', 'No relevant results were returned'],
      ['unavailable', 'The source provider is unavailable'],
    ]) {
      if (await evaluate(popup, `Boolean(document.querySelector('[aria-label="Analysis result"]'))`)) {
        await clickText(popup, 'Check again');
        await waitFor(popup, 'Boolean(document.querySelector("#screen-text"))');
      }
      const controlled = { ...actualFixture, analyzed_text: `Controlled ${retrievalStatus} display fixture.`, retrieval_status: retrievalStatus, related_sources: [] };
      await evaluate(popup, `window.fetch=async()=>new Response(${JSON.stringify(JSON.stringify(controlled))},{status:200,headers:{'Content-Type':'application/json'}}); true`);
      await setValue(popup, '#screen-text', controlled.analyzed_text);
      await clickText(popup, 'Analyze text');
      await waitFor(popup, `document.body.innerText.includes(${JSON.stringify(expectedText)})`, 15000);
    }

    await evaluate(popup, `window.fetch=(_url,options)=>new Promise((_resolve,reject)=>options.signal.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError')))); true`);
    if (await evaluate(popup, `Boolean(document.querySelector('[aria-label="Analysis result"]'))`)) {
      await clickText(popup, 'Check again');
      await waitFor(popup, 'Boolean(document.querySelector("#screen-text"))');
    }
    await setValue(popup, '#screen-text', 'Synthetic timeout rehearsal.');
    await clickText(popup, 'Analyze text');
    await waitFor(popup, 'document.querySelector("[role=alert]")?.textContent.includes("timed out")', 15000);
    await screenshot(popup, 'popup-installed-failure-states');
    const failureReport = {
      passed: true,
      browser: `${path.basename(CHROME).toLowerCase().includes('msedge') ? 'Microsoft Edge' : 'Google Chrome'} (isolated off-screen profile)`,
      extension_page_opened_directly: true,
      actual_unavailable_backend: 'passed', clear_unavailable_message: 'passed',
      controlled_timeout_ui: 'passed', controlled_no_results_ui: 'passed', controlled_provider_failure_ui: 'passed',
      timeout_test_build_ms: 100, normal_build_restored_ms: 120000,
      classifier_note: 'No prediction was created for unavailable or timeout requests. No-results/failure display used a previously generated actual model result; provider behavior is separately backend-tested.',
    };
    await writeFile(path.join(ROOT, 'docs', 'EXTENSION-FAILURE-VERIFICATION.json'), JSON.stringify(failureReport, null, 2) + '\n');
    console.log(JSON.stringify(failureReport, null, 2));
  } else {
  await waitFor(popup, 'Boolean(document.querySelector("#screen-text"))', 20000);
  const popupText = await evaluate(popup, 'document.body.innerText');
  assert.ok(!/participant|research receipts|voluntarily consent|usefulness rating/i.test(popupText));
  await screenshot(popup, 'popup-installed-empty');

  await clickText(popup, 'Analyze text');
  await waitFor(popup, 'Boolean(document.querySelector("[role=alert]"))');
  assert.match(await evaluate(popup, 'document.body.innerText'), /Enter or select text/);
  await evaluate(popup, `(() => { const input=document.querySelector('fieldset.choices input[type=checkbox]'); if(input?.checked) input.click(); return input?.checked===false; })()`);

  const shortText = 'BREAKING!!! Share agad!!! Totoo ba ito?';
  await setValue(popup, '#screen-text', shortText);
  let analyzeRequests = 0;
  let sourceLookupRequests = 0;
  popup.listeners.push(message => {
    if (message.method !== 'Network.requestWillBeSent') return;
    if (message.params?.request?.url.endsWith('/analyze')) analyzeRequests++;
    if (message.params?.request?.url.endsWith('/related-sources')) sourceLookupRequests++;
  });
  await popup.send('Network.enable');
  await evaluate(popup, `(() => { const button=[...document.querySelectorAll('button')].find(n=>n.textContent.includes('Analyze text')); button.click(); button.click(); return true; })()`);
  await waitFor(popup, `Boolean(document.querySelector('[aria-label="Analysis result"]'))`);
  assert.equal(analyzeRequests, 1);
  const popupLabel = await evaluate(popup, `document.querySelector('[aria-label="Analysis result"] h2').textContent`);
  const popupScore = Number((await evaluate(popup, 'document.querySelector(".score strong").textContent')).replace(/[<>%]/g, '')) / 100;
  const apiResult = await fetch('http://127.0.0.1:8000/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: shortText }) }).then(response => response.json());
  const expectedLabel = apiResult.internal_label === 'Misleading' ? 'Potentially Misleading' : 'No Misleading Information Detected';
  assert.equal(popupLabel, expectedLabel);
  assert.ok(Math.abs(popupScore - apiResult.displayed_class_score) < 0.00011);
  assert.ok((await evaluate(popup, 'document.body.innerText')).includes('Post context'));
  assert.ok((await evaluate(popup, 'document.body.innerText')).includes('Manually entered text'));
  const resultOrder = await evaluate(popup, `[...document.querySelectorAll('[data-result-part]')].map(node=>node.dataset.resultPart)`);
  assert.deepEqual(resultOrder, ['1-prediction', '2-score', '3-post-context', '4-features', '5-related-sources', '6-analyzed-text', '7-reminder', '8-check-again']);
  const englishReminder = 'SuriPH is an automated screening tool that may produce incorrect predictions. Its label and score do not confirm whether a claim is true or false. Review the original post’s date, source and full context, and consult credible references before sharing or acting on the information.';
  assert.equal(await evaluate(popup, `[...document.querySelectorAll('[data-result-part="7-reminder"]')].filter(node=>node.textContent===${JSON.stringify(englishReminder)}).length`), 1);
  const popupFeatures = await evaluate(popup, '[...document.querySelectorAll("[data-feature]")].map(n=>[n.dataset.feature,Number(n.dataset.value)])');
  assert.deepEqual(Object.fromEntries(popupFeatures), Object.fromEntries(apiResult.linguistic_indicators.map(item => [item.name, item.value])));

  await clickText(popup, 'Find related sources');
  await waitFor(popup, '!document.body.innerText.includes("Finding related sources")', 30000);
  assert.equal(sourceLookupRequests, 1, 'Find related sources must make one source-only request');
  assert.equal(analyzeRequests, 1, 'Source lookup must not rerun inference');
  assert.ok(!(await evaluate(popup, 'document.body.innerText')).includes('Source lookup was not requested.'));

  const resultBeforeLanguageSwitch = await evaluate(popup, `JSON.stringify({label:document.querySelector('[aria-label="Analysis result"] h2').textContent,score:document.querySelector('.score strong').textContent,text:document.querySelector('.input-preview').textContent,features:[...document.querySelectorAll('[data-feature]')].map(node=>node.dataset.value)})`);
  await clickText(popup, 'Tagalog');
  await waitFor(popup, `document.body.innerText.includes('Detalye ng linguistic features')`);
  const resultAfterLanguageSwitch = await evaluate(popup, `JSON.stringify({label:document.querySelector('[aria-label="Analysis result"] h2').textContent,score:document.querySelector('.score strong').textContent,text:document.querySelector('.input-preview').textContent,features:[...document.querySelectorAll('[data-feature]')].map(node=>node.dataset.value)})`);
  assert.equal(resultAfterLanguageSwitch, resultBeforeLanguageSwitch);
  assert.equal(analyzeRequests, 1, 'Language switching must not make another inference request');
  assert.ok((await evaluate(popup, 'document.body.scrollWidth <= document.body.clientWidth')));
  await clickText(popup, 'English');

  await clickText(popup, 'Check again');
  await waitFor(popup, 'Boolean(document.querySelector("#screen-text"))');
  await setValue(popup, '#screen-text', 'changed input clears old result');
  assert.equal(await evaluate(popup, `Boolean(document.querySelector('[aria-label="Analysis result"]'))`), false);
  const tail = 'SURIPH_COMPLETE_TEXT_TAIL';
  const longText = `${'Basahin ang buong ulat bago mag share. '.repeat(350)}${tail}`;
  await setValue(popup, '#screen-text', longText);
  await clickText(popup, 'Analyze text');
  await waitFor(popup, `Boolean(document.querySelector('[aria-label="Analysis result"]'))`);
  assert.equal(await evaluate(popup, `document.querySelector('.input-preview').textContent.endsWith(${JSON.stringify(tail)})`), true);

  let diagnostics = null;
  if (process.env.SURI_DIAGNOSTIC_TEXT_FILE) {
    const rawDiagnostic = (await readFile(process.env.SURI_DIAGNOSTIC_TEXT_FILE, 'utf8')).replace(/^\uFEFF/, '').trim();
    let diagnosticInputs;
    try {
      const parsed = JSON.parse(rawDiagnostic);
      diagnosticInputs = parsed.exact_inputs || parsed;
      assert.equal(typeof diagnosticInputs, 'object');
      assert.equal(Array.isArray(diagnosticInputs), false);
    } catch {
      diagnosticInputs = { diagnostic_text: rawDiagnostic };
    }
    diagnostics = {};
    for (const [diagnosticKey, diagnosticText] of Object.entries(diagnosticInputs)) {
      assert.equal(typeof diagnosticText, 'string');
      await clickText(popup, 'Check again');
      await waitFor(popup, 'Boolean(document.querySelector("#screen-text"))');
      await evaluate(popup, `(() => { const input=document.querySelector('fieldset.choices input[type=checkbox]'); if(input?.checked) input.click(); return true; })()`);
      await setValue(popup, '#screen-text', diagnosticText);
      await clickText(popup, 'Analyze text');
      await waitFor(popup, `Boolean(document.querySelector('[aria-label="Analysis result"]'))`);
      const diagnosticUi = {
        label: await evaluate(popup, `document.querySelector('[aria-label="Analysis result"] h2').textContent`),
        displayedPercent: await evaluate(popup, `document.querySelector('.score strong').textContent`),
        analyzedTextMatches: await evaluate(popup, `document.querySelector('.input-preview').textContent===${JSON.stringify(diagnosticText)}`),
      };
      const diagnosticApi = await fetch('http://127.0.0.1:8000/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: diagnosticText }) }).then(response => response.json());
      const diagnosticExpectedLabel = diagnosticApi.internal_label === 'Misleading' ? 'Potentially Misleading' : 'No Misleading Information Detected';
      assert.equal(diagnosticUi.label, diagnosticExpectedLabel);
      assert.equal(diagnosticUi.displayedPercent, displayPercent(diagnosticApi.displayed_class_score));
      assert.equal(diagnosticUi.analyzedTextMatches, true);
      diagnostics[diagnosticKey] = {
        text_sha256: createHash('sha256').update(diagnosticText).digest('hex'),
        api_label: diagnosticApi.internal_label,
        api_model_score: diagnosticApi.model_score,
        ui_label: diagnosticUi.label,
        ui_displayed_percent: diagnosticUi.displayedPercent,
        ui_analyzed_text_matches: true,
      };
    }
  }

  await screenshot(popup, 'popup-installed-result');

  const report = {
    passed: true,
    browser: `${path.basename(CHROME).toLowerCase().includes('msedge') ? 'Microsoft Edge' : 'Google Chrome'} (isolated off-screen profile)`,
    unpacked_extension_loaded: true,
    extension_id_observed: true,
    popup_opened_from_action: actionAvailable,
    popup_opened_as_extension_window: !actionAvailable,
    actual_backend_connection: true,
    empty_input: 'passed', manual_text_prediction: 'passed', duplicate_click_single_request: 'passed',
    stale_result_cleared: 'passed', long_text_tail_preserved: 'passed', seven_feature_values_match_backend: 'passed', context_visible: 'passed', exact_eight_part_order: 'passed', one_bottom_reminder: 'passed',
    source_only_lookup_without_reclassification: 'passed',
    diagnostic_text_path_comparisons: diagnostics,
    bilingual_switch_preserves_result_without_request: 'passed', narrow_width_no_horizontal_clipping: 'passed',
    survey_controls_absent: 'passed', screenshots_private: true,
    content_script_facebook_extraction: 'covered separately by FACEBOOK-MODAL-VERIFICATION.json on a synthetic HTTPS facebook.com fixture; actual Google Chrome/Facebook interaction remains manual',
    limitations: ['No real social account or participant content was used.', 'Keyboard and screen-reader testing remains manual.'],
  };
  await writeFile(path.join(ROOT, 'docs', 'EXTENSION-POPUP-VERIFICATION.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
  }
} finally {
  clearInterval(keepAlive);
  popup?.close();
  if (process.platform === 'win32') spawnSync('taskkill', ['/PID', String(chrome.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
  else chrome.kill('SIGKILL');
  chrome.unref();
}
