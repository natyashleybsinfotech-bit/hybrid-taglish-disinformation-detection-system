// Exercise the unpacked extension's real action popup against the running API.
// The Chrome profile and screenshots remain under ignored tmp/.
import assert from 'node:assert/strict';
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
const keepAlive = setInterval(() => {}, 1000);

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
  const actionAvailable = await workerEvaluate('Boolean(chrome.action?.openPopup)');
  if (actionAvailable) await workerEvaluate('chrome.action.openPopup().then(()=>true)', true);
  else await workerEvaluate(`chrome.windows.create({url:chrome.runtime.getURL('index.html'),type:'popup',width:420,height:900}).then(()=>true)`, true);
  worker.close();
  let popupTarget;
  for (let attempt = 0; attempt < 100 && !popupTarget; attempt++) {
    popupTarget = (await targets(port)).find(item => item.type === 'page' && item.url === `chrome-extension://${extensionId}/index.html`);
    await wait(100);
  }
  assert.ok(popupTarget, 'Extension action popup did not open');
  popup = await new CDP(popupTarget.webSocketDebuggerUrl).open();
  await wait(1000);
  if (process.env.SURI_CDP_DEBUG === '1') console.error(await evaluate(popup, 'JSON.stringify({url:location.href,html:document.body?.innerHTML?.slice(0,500)})'));
  await waitFor(popup, 'Boolean(document.querySelector("#screen-text"))', 10000);
  await waitFor(popup, 'document.body.innerText.includes("Server retention:")', 20000);
  await screenshot(popup, 'popup-installed-empty');

  await clickText(popup, 'Analyze text');
  await waitFor(popup, 'Boolean(document.querySelector("[role=alert]"))');
  assert.match(await evaluate(popup, 'document.body.innerText'), /Enter or select text/);

  const shortText = 'BREAKING!!! Share agad!!! Totoo ba ito?';
  await setValue(popup, '#screen-text', shortText);
  let analyzeRequests = 0;
  popup.listeners.push(message => { if (message.method === 'Network.requestWillBeSent' && message.params?.request?.url.endsWith('/analyze')) analyzeRequests++; });
  await popup.send('Network.enable');
  await evaluate(popup, `(() => { const button=[...document.querySelectorAll('button')].find(n=>n.textContent.includes('Analyze text')); button.click(); button.click(); return true; })()`);
  await waitFor(popup, `Boolean(document.querySelector('[aria-label="Analysis result"]'))`);
  assert.equal(analyzeRequests, 1);
  const popupLabel = await evaluate(popup, `document.querySelector('[aria-label="Analysis result"] h2').textContent`);
  const popupScore = Number((await evaluate(popup, 'document.querySelector(".score strong").textContent')).replace(/[<>%]/g, '')) / 100;
  const apiResult = await fetch('http://127.0.0.1:8000/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: shortText }) }).then(response => response.json());
  assert.equal(popupLabel, apiResult.internal_label);
  assert.ok(Math.abs(popupScore - apiResult.model_score) < 0.00011);
  const popupFeatures = await evaluate(popup, '[...document.querySelectorAll("[data-feature]")].map(n=>[n.dataset.feature,Number(n.dataset.value)])');
  assert.deepEqual(Object.fromEntries(popupFeatures), Object.fromEntries(apiResult.linguistic_indicators.map(item => [item.name, item.value])));

  await setValue(popup, '#screen-text', 'changed input clears old result');
  assert.equal(await evaluate(popup, `Boolean(document.querySelector('[aria-label="Analysis result"]'))`), false);
  const tail = 'SURIPH_COMPLETE_TEXT_TAIL';
  const longText = `${'Basahin ang buong ulat bago mag share. '.repeat(350)}${tail}`;
  await setValue(popup, '#screen-text', longText);
  await clickText(popup, 'Analyze text');
  await waitFor(popup, `Boolean(document.querySelector('[aria-label="Analysis result"]'))`);
  assert.equal(await evaluate(popup, `document.querySelector('.input-preview').textContent.endsWith(${JSON.stringify(tail)})`), true);

  await setValue(popup, '#screen-text', 'Synthetic consent rehearsal only.');
  await evaluate(popup, `(() => { const boxes=[...document.querySelectorAll('input[type=checkbox]')]; const consent=boxes.find(n=>n.parentElement.textContent.includes('voluntarily consent')); consent.click(); return consent.checked; })()`);
  await clickText(popup, 'Analyze text');
  await waitFor(popup, 'document.body.innerText.includes("Research receipts and feedback (1)")');
  await evaluate(popup, `(() => { const select=document.querySelector('.receipt select'); select.value='4'; select.dispatchEvent(new Event('change',{bubbles:true})); return true; })()`);
  await waitFor(popup, 'document.body.innerText.includes("usefulness rating was saved")');
  await clickText(popup, 'Delete this saved record');
  await waitFor(popup, 'document.body.innerText.includes("saved research record was deleted")');
  assert.equal(await evaluate(popup, 'document.querySelectorAll(".receipt").length'), 0);
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
    stale_result_cleared: 'passed', long_text_tail_preserved: 'passed', seven_feature_values_match_backend: 'passed',
    consent_feedback_withdrawal: 'passed', screenshots_private: true,
    content_script_social_extraction: 'covered by the separate installed-extension rehearsal',
    limitations: ['No real social account or participant content was used.', 'Keyboard and screen-reader testing remains manual.'],
  };
  await writeFile(path.join(ROOT, 'docs', 'EXTENSION-POPUP-VERIFICATION.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
} finally {
  clearInterval(keepAlive);
  popup?.close();
  if (process.platform === 'win32') spawnSync('taskkill', ['/PID', String(chrome.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
  else chrome.kill('SIGKILL');
  chrome.unref();
}
