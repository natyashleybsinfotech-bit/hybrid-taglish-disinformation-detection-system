// Real Chrome extension and administrator-flow rehearsal using an isolated profile.
// Screenshots and the profile stay under ignored tmp/. No participant data is used.
import assert from 'node:assert/strict';
import { createHash, createHmac, X509Certificate } from 'node:crypto';
import { spawn, spawnSync } from 'node:child_process';
import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import { createServer } from 'node:https';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const CHROME = process.env.SURI_TEST_BROWSER || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const EXTENSION = path.join(ROOT, 'chrome-extension', 'dist');
const RUN = path.join(ROOT, 'tmp', `installed-extension-${Date.now()}`);
const PROFILE = path.join(RUN, 'profile');
const SHOTS = path.join(RUN, 'screenshots');
const DOWNLOADS = path.join(RUN, 'downloads');
await Promise.all([mkdir(PROFILE, { recursive: true }), mkdir(SHOTS, { recursive: true }), mkdir(DOWNLOADS, { recursive: true })]);

const certPath = path.join(RUN, 'fixture.cer');
const pfxPath = path.join(RUN, 'fixture.pfx');
const certificateScript = [
  "$rsa=[Security.Cryptography.RSA]::Create(2048)",
  "$request=[Security.Cryptography.X509Certificates.CertificateRequest]::new('CN=www.facebook.com',$rsa,[Security.Cryptography.HashAlgorithmName]::SHA256,[Security.Cryptography.RSASignaturePadding]::Pkcs1)",
  "$san=[Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder]::new()",
  "$san.AddDnsName('www.facebook.com')",
  "$request.CertificateExtensions.Add($san.Build())",
  "$cert=$request.CreateSelfSigned([DateTimeOffset]::UtcNow.AddMinutes(-5),[DateTimeOffset]::UtcNow.AddHours(2))",
  "[IO.File]::WriteAllBytes($env:SURI_CERT_OUT,$cert.Export([Security.Cryptography.X509Certificates.X509ContentType]::Cert))",
  "[IO.File]::WriteAllBytes($env:SURI_PFX_OUT,$cert.Export([Security.Cryptography.X509Certificates.X509ContentType]::Pfx,'suriph-fixture'))",
  "$cert.Dispose();$rsa.Dispose()",
].join(';');
const certificate = spawnSync('powershell.exe', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', certificateScript], {
  windowsHide: true, encoding: 'utf8', env: { ...process.env, SURI_CERT_OUT: certPath, SURI_PFX_OUT: pfxPath },
});
assert.equal(certificate.status, 0, `Could not create isolated fixture certificate: ${certificate.stderr}`);

function envFile(file) {
  return Object.fromEntries(file.split(/\r?\n/).filter(line => line && !line.trimStart().startsWith('#') && line.includes('='))
    .map(line => { const index = line.indexOf('='); return [line.slice(0, index), line.slice(index + 1)]; }));
}
const privateEnv = envFile(await readFile(path.join(ROOT, 'backend-api', '.env.local'), 'utf8'));
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const fixtureHtml = `<!doctype html><meta charset="utf-8"><title>Synthetic supported-page fixture</title><article role="article" tabindex="0"><h2>Researcher Fixture</h2><p id="caption">BREAKING!!! Share agad!!! Totoo ba ito?</p><time datetime="2026-10-20T08:00:00Z">2h</time></article>`;
const fixtureCertificate = new X509Certificate(await readFile(certPath));
const fixtureSpki = createHash('sha256').update(fixtureCertificate.publicKey.export({ type: 'spki', format: 'der' })).digest('base64');
const fixtureServer = createServer({ pfx: await readFile(pfxPath), passphrase: 'suriph-fixture' }, (_request, response) => { response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' }); response.end(fixtureHtml); });
await new Promise((resolve, reject) => { fixtureServer.once('error', reject); fixtureServer.listen(0, '127.0.0.1', resolve); });
const fixturePort = fixtureServer.address().port;

class CDP {
  constructor(url) { this.url = url; this.id = 0; this.pending = new Map(); this.listeners = []; }
  async open() {
    this.socket = new WebSocket(this.url);
    await new Promise((resolve, reject) => { this.socket.onopen = resolve; this.socket.onerror = reject; });
    this.socket.onmessage = event => {
      const message = JSON.parse(event.data);
      for (const listener of this.listeners) listener(message);
      if (!message.id || !this.pending.has(message.id)) return;
      const { resolve, reject } = this.pending.get(message.id); this.pending.delete(message.id);
      message.error ? reject(new Error(`${message.error.message}: ${JSON.stringify(message.error.data || '')}`)) : resolve(message.result || {});
    };
    this.socket.onclose = () => {
      for (const { reject } of this.pending.values()) reject(new Error('The browser target closed.'));
      this.pending.clear();
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
async function newTarget(port, url) {
  const target = await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(url)}`, { method: 'PUT' }).then(response => response.json());
  const client = await new CDP(target.webSocketDebuggerUrl).open();
  await Promise.all([client.send('Page.enable'), client.send('Runtime.enable'), client.send('Network.enable')]);
  return { target, client };
}
async function evaluate(client, expression, awaitPromise = false) {
  const output = await client.send('Runtime.evaluate', { expression, awaitPromise, returnByValue: true, userGesture: true });
  if (output.exceptionDetails) throw new Error(output.exceptionDetails.exception?.description || output.exceptionDetails.text);
  return output.result?.value;
}
async function waitFor(client, expression, timeout = 120000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) { try { if (await evaluate(client, expression, true)) return; } catch {} await wait(100); }
  throw new Error(`Timed out waiting for: ${expression.slice(0, 120)}`);
}
async function screenshot(client, name, width = 390, height = 900) {
  try { await client.send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false }); }
  catch (error) { if (!String(error).includes('does not support metrics override')) throw error; }
  const result = await client.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  await writeFile(path.join(SHOTS, `${name}.png`), Buffer.from(result.data, 'base64'));
}
async function setControl(client, selector, value) {
  await evaluate(client, `(() => { const element=document.querySelector(${JSON.stringify(selector)}); if(!element) throw new Error('Missing ${selector}'); const proto=element instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype; Object.getOwnPropertyDescriptor(proto,'value').set.call(element,${JSON.stringify(value)}); element.dispatchEvent(new Event('input',{bubbles:true})); element.dispatchEvent(new Event('change',{bubbles:true})); return true; })()`);
}
async function clickText(client, label) {
  return evaluate(client, `(() => { const target=[...document.querySelectorAll('button,summary,a')].find(node=>node.textContent.trim().includes(${JSON.stringify(label)})); if(!target) throw new Error('Missing control: ${label}'); target.click(); return true; })()`);
}
async function bodyText(client) { return evaluate(client, 'document.body.innerText'); }
async function waitForPopupToClose(port, extensionId) {
  const popupUrl = `chrome-extension://${extensionId}/index.html`;
  const deadline = Date.now() + 10000;
  while (Date.now() < deadline) {
    if (!(await targets(port)).some(item => item.type === 'page' && item.url === popupUrl)) return;
    await wait(100);
  }
  throw new Error('The extension popup did not close after reloading the active page');
}
async function reopenPopup(port, extensionId, socialClient) {
  await socialClient.send('Page.bringToFront');
  const popupUrl = `chrome-extension://${extensionId}/index.html`;
  let popupTarget = (await targets(port)).find(item => item.type === 'page' && item.url === popupUrl);
  if (!popupTarget) {
    const workerTarget = (await targets(port)).find(item => item.type === 'service_worker' && item.url.startsWith(`chrome-extension://${extensionId}/`));
    assert.ok(workerTarget, 'Extension service worker was not active');
    const worker = await new CDP(workerTarget.webSocketDebuggerUrl).open();
    try { await evaluate(worker, 'chrome.action.openPopup().then(()=>true)', true); } finally { worker.close(); }
  }
  const deadline = Date.now() + 10000;
  while (Date.now() < deadline) {
    popupTarget = (await targets(port)).find(item => item.type === 'page' && item.url === popupUrl);
    if (popupTarget) { const client = await new CDP(popupTarget.webSocketDebuggerUrl).open(); await Promise.all([client.send('Page.enable'), client.send('Runtime.enable')]); await waitFor(client, 'Boolean(document.querySelector("#screen-text"))', 10000); return client; }
    await wait(100);
  }
  throw new Error('The real extension action popup did not open');
}

const chrome = spawn(CHROME, [
  '--disable-gpu', '--no-sandbox', '--no-first-run', '--no-default-browser-check', '--window-size=1200,900', '--window-position=-32000,-32000',
  `--user-data-dir=${PROFILE}`, '--remote-debugging-port=0',
  '--host-resolver-rules=MAP www.facebook.com 127.0.0.1', `--ignore-certificate-errors-spki-list=${fixtureSpki}`, `--explicitly-allowed-ports=${fixturePort}`,
  `--disable-extensions-except=${EXTENSION}`, `--load-extension=${EXTENSION}`, 'about:blank',
], { windowsHide: false, stdio: 'ignore' });
const clients = [];
try {
  let port;
  for (let attempt = 0; attempt < 200; attempt++) { try { port = Number((await readFile(path.join(PROFILE, 'DevToolsActivePort'), 'utf8')).split(/\r?\n/)[0]); break; } catch { await wait(100); } }
  assert.ok(port, 'Chrome remote debugging did not start');
  let extensionId;
  for (let attempt = 0; attempt < 100; attempt++) { const worker = (await targets(port)).find(item => item.type === 'service_worker' && item.url.endsWith('/service-worker-loader.js')); if (worker) { extensionId = new URL(worker.url).hostname; break; } await wait(100); }
  assert.ok(extensionId, 'Unpacked SuriPH extension did not register a service worker');

  const social = await newTarget(port, `https://www.facebook.com:${fixturePort}/fixture`); clients.push(social.client);
  await waitFor(social.client, 'Boolean(document.querySelector("#suriph-control-host")?.shadowRoot)');
  assert.equal(await evaluate(social.client, 'document.querySelectorAll("#suriph-control-host").length'), 1);

  let popup = await reopenPopup(port, extensionId, social.client); clients.push(popup);
  await waitFor(popup, 'document.body.innerText.includes("Server retention:")', 20000);
  await screenshot(popup, 'popup-installed-empty');

  await clickText(popup, 'Analyze text');
  await waitFor(popup, 'Boolean(document.querySelector("[role=alert]"))');
  assert.match(await bodyText(popup), /Enter or select text/);

  const selected = 'Share agad!!! Totoo ba ito?';
  await evaluate(social.client, `(() => { const node=document.querySelector('#caption').firstChild; const range=document.createRange(); range.setStart(node,node.textContent.indexOf('Share')); range.setEnd(node,node.textContent.length); const selection=getSelection(); selection.removeAllRanges(); selection.addRange(range); return selection.toString(); })()`);
  await clickText(popup, 'Use selected text');
  await waitFor(popup, `document.querySelector('#screen-text').value===${JSON.stringify(selected)}`);
  assert.equal(await evaluate(popup, 'document.querySelector("#screen-text").value'), selected);

  await evaluate(social.client, 'getSelection().removeAllRanges(); document.querySelector("article").focus(); true');
  await clickText(popup, 'Use post caption');
  await waitFor(popup, 'document.querySelector("#screen-text").value.includes("BREAKING")');
  assert.match(await evaluate(popup, 'document.querySelector("#screen-text").value'), /Researcher Fixture.*BREAKING/);

  await clickText(popup, 'Page tools on');
  await waitFor(social.client, '!document.querySelector("#suriph-control-host")');
  popup.close();
  await waitForPopupToClose(port, extensionId);
  popup = await reopenPopup(port, extensionId, social.client); clients.push(popup);
  await clickText(popup, 'Page tools off');
  await waitFor(social.client, 'Boolean(document.querySelector("#suriph-control-host"))');

  const manual = 'Basahin muna ang buong balita bago mag-share. Check the original source.';
  await setControl(popup, '#screen-text', manual);
  await clickText(popup, 'Analyze text');
  await waitFor(popup, 'document.querySelectorAll("[data-feature]").length===7', 180000);
  const rendered = await evaluate(popup, '[...document.querySelectorAll("[data-feature]")].map(node=>({name:node.dataset.feature,value:Number(node.dataset.value)}))');
  const direct = await fetch('http://127.0.0.1:8000/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: manual }) }).then(response => response.json());
  assert.equal(direct.linguistic_indicators.length, 7);
  for (const item of direct.linguistic_indicators) assert.equal(rendered.find(row => row.name === item.name)?.value, item.value);
  await screenshot(popup, 'popup-installed-result', 390, 1100);

  await setControl(popup, '#screen-text', 'Changed input must clear the previous result.');
  assert.equal(await evaluate(popup, 'document.querySelectorAll("[data-feature]").length'), 0, 'Changing input left a stale result');

  let analyzeRequests = 0;
  popup.listeners.push(message => { if (message.method === 'Network.requestWillBeSent' && message.params?.request?.url.endsWith('/analyze')) analyzeRequests++; });
  await popup.send('Network.enable');
  await evaluate(popup, `(() => { const button=[...document.querySelectorAll('button')].find(node=>node.textContent.includes('Analyze text')); button.click(); button.click(); return button.disabled; })()`);
  await waitFor(popup, 'document.querySelectorAll("[data-feature]").length===7', 180000);
  assert.equal(analyzeRequests, 1, 'Repeated click did not create exactly one request');

  const longText = 'Basahin natin ang buong artikulo at suriin ang source. '.repeat(100) + 'UNIQUE_TAIL_73129';
  await setControl(popup, '#screen-text', longText);
  await clickText(popup, 'Analyze text');
  await waitFor(popup, 'document.querySelectorAll("[data-feature]").length===7', 180000);
  assert.ok((await evaluate(popup, 'document.querySelector(".input-preview")?.textContent || ""')).endsWith('UNIQUE_TAIL_73129'));

  await setControl(popup, '#screen-text', 'PAGASA official weather advisory Philippines');
  await evaluate(popup, `(() => { const input=[...document.querySelectorAll('label')].find(node=>node.textContent.includes('Search related sources'))?.querySelector('input'); if(!input.checked) input.click(); return input.checked; })()`);
  await clickText(popup, 'Analyze text');
  await waitFor(popup, 'document.querySelectorAll("[data-feature]").length===7', 180000);
  const sourceLinks = await evaluate(popup, 'document.querySelectorAll("article.source a").length');

  await evaluate(popup, `(() => { const label=[...document.querySelectorAll('label')].find(node=>node.textContent.includes('voluntarily consent')); const input=label?.querySelector('input'); if(!input.checked) input.click(); return input.checked; })()`);
  await setControl(popup, '#screen-text', 'Synthetic consent rehearsal record; no participant content.');
  await clickText(popup, 'Analyze text');
  await waitFor(popup, 'document.querySelectorAll("article.receipt").length===1', 180000);
  await evaluate(popup, `(() => { const select=document.querySelector('article.receipt select'); select.value='5'; select.dispatchEvent(new Event('change',{bubbles:true})); return true; })()`);
  await waitFor(popup, 'document.body.innerText.includes("usefulness rating was saved")', 30000);
  await clickText(popup, 'Delete this saved record');
  await waitFor(popup, 'document.body.innerText.includes("saved research record was deleted")', 30000);
  assert.equal(await evaluate(popup, 'document.querySelectorAll("article.receipt").length'), 0);

  const admin = await newTarget(port, 'http://127.0.0.1:5173/'); clients.push(admin.client);
  await waitFor(admin.client, 'Boolean(document.querySelector("input[autocomplete=username]"))', 30000);
  await screenshot(admin.client, 'admin-actual-login', 1280, 900);
  await setControl(admin.client, 'input[autocomplete=username]', privateEnv.SURI_ADMIN_USERNAME);
  await setControl(admin.client, 'input[autocomplete=current-password]', privateEnv.SURI_ADMIN_PASSWORD);
  await clickText(admin.client, 'Continue');
  await waitFor(admin.client, 'document.body.innerText.includes("System status") && document.body.innerText.includes("Log out")', 30000);
  await admin.client.send('Page.reload', { ignoreCache: true });
  await waitFor(admin.client, 'document.body.innerText.includes("Log out")', 30000);
  const sessionPersisted = !(await bodyText(admin.client)).includes('Enter your credentials');
  await evaluate(admin.client, 'history.pushState({},"","/research"); window.dispatchEvent(new PopStateEvent("popstate")); true');
  await waitFor(admin.client, 'document.body.innerText.includes("Download research CSV")', 30000);
  await screenshot(admin.client, 'admin-actual-research', 1280, 900);
  await admin.client.send('Page.setDownloadBehavior', { behavior: 'allow', downloadPath: DOWNLOADS });
  await clickText(admin.client, 'Download research CSV');
  for (let attempt = 0; attempt < 100 && !(await readdir(DOWNLOADS)).some(name => name.endsWith('.csv')); attempt++) await wait(100);
  const exportName = (await readdir(DOWNLOADS)).find(name => name.endsWith('.csv'));
  assert.ok(exportName, 'Research export did not download');
  const exportText = await readFile(path.join(DOWNLOADS, exportName), 'utf8');
  assert.ok(exportText.startsWith('record_id,consent_version,input_type,usefulness,label,model_score,training_run_id,artifact_sha256,features_json'));
  assert.ok(!exportText.includes('Synthetic consent rehearsal'));
  await clickText(admin.client, 'Log out');
  await waitFor(admin.client, 'document.body.innerText.includes("Enter your credentials")', 30000);
  const afterLogout = await fetch('http://127.0.0.1:8000/admin-api/check-auth').then(response => response.status);
  assert.equal(afterLogout, 401);

  await setControl(admin.client, 'input[autocomplete=username]', privateEnv.SURI_VIEWER_USERNAME);
  await setControl(admin.client, 'input[autocomplete=current-password]', privateEnv.SURI_VIEWER_PASSWORD);
  await clickText(admin.client, 'Continue');
  await waitFor(admin.client, 'document.body.innerText.includes("view only")', 30000);
  assert.ok(!(await bodyText(admin.client)).includes('Participant research'));
  const viewerStatus = await evaluate(admin.client, `fetch('http://127.0.0.1:8000/admin-api/research-export',{credentials:'include'}).then(response=>response.status)`, true);
  assert.equal(viewerStatus, 403);
  await clickText(admin.client, 'Log out');

  const payload = Buffer.from(JSON.stringify({ username: 'expired-fixture', role: 'admin', expires: 1 })).toString('base64url');
  const signature = createHmac('sha256', privateEnv.SURI_SESSION_SECRET).update(payload).digest('hex');
  const expiredStatus = await fetch('http://127.0.0.1:8000/admin-api/check-auth', { headers: { Cookie: `suriph_admin_token=${payload}.${signature}` } }).then(response => response.status);
  assert.equal(expiredStatus, 401);

  const report = {
    passed: true, browser: path.basename(CHROME).toLowerCase().includes('msedge') ? 'Microsoft Edge' : 'Google Chrome', isolated_profile: true, unpacked_extension_loaded: true,
    extension_id_observed: true, popup_opened_from_action: true, actual_backend: true,
    manual_text: 'passed', empty_input: 'passed', selected_text: 'passed', supported_caption_fixture: 'passed',
    page_tools_reload_toggle: 'passed', repeated_submission_single_request: 'passed', stale_result_cleared: 'passed',
    long_input_complete_tail: 'passed', seven_feature_values_match_backend: 'passed',
    live_evidence_links_returned: sourceLinks, consent_feedback_withdrawal: 'passed',
    admin_login_logout: 'passed', admin_session_reload_persistence: sessionPersisted ? 'passed' : 'failed',
    admin_export: 'passed', viewer_export_status: viewerStatus, expired_session_status: expiredStatus,
    screenshots_private: true, screenshot_directory: path.relative(ROOT, SHOTS).replaceAll('\\', '/'),
    social_scope: 'Synthetic article fixture on a manifest-supported facebook.com origin; no account, post, message or participant data.',
    not_tested_here: ['manual Chrome installation (Chrome ignored command-line unpacked loading)', 'actual changing third-party DOM', 'screen reader', 'Chrome Web Store build', 'provider timeout in popup'],
  };
  assert.equal(report.admin_session_reload_persistence, 'passed');
  await writeFile(path.join(ROOT, 'docs', 'INSTALLED-EXTENSION-VERIFICATION.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
} finally {
  for (const client of clients) client.close();
  fixtureServer.close();
  if (process.platform === 'win32') spawnSync('taskkill', ['/PID', String(chrome.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
  else chrome.kill('SIGKILL');
}
process.exit(0);
