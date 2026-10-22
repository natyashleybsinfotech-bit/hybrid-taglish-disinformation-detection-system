// Exercise the real content script on an isolated local facebook.com fixture.
import assert from 'node:assert/strict';
import { createHash, X509Certificate } from 'node:crypto';
import { spawn, spawnSync } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createServer } from 'node:https';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const BROWSER = process.env.SURI_TEST_BROWSER || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const EXTENSION = path.join(ROOT, 'chrome-extension', 'dist');
const RUN = path.join(ROOT, 'tmp', `facebook-modal-${Date.now()}`);
const PROFILE = path.join(RUN, 'profile');
const SHOTS = path.join(RUN, 'screenshots');
await Promise.all([mkdir(PROFILE, { recursive: true }), mkdir(SHOTS, { recursive: true })]);

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
assert.equal(certificate.status, 0, `Could not create fixture certificate: ${certificate.stderr}`);

const fixtureHtml = `<!doctype html><meta charset="utf-8"><title>SuriPH Facebook fixture</title>
<article role="article" tabindex="0">
  <h2><a role="link" href="https://www.facebook.com/researcher.fixture">Researcher Fixture</a></h2>
  <p data-ad-comet-preview="message">BREAKING!!! Share agad!!! Totoo ba ito?</p>
  <time datetime="2026-10-20T08:00:00Z">October 20 at 4:00 PM</time>
  <a href="https://www.facebook.com/researcher.fixture/posts/123">Original post</a>
  <a href="https://example.org/reference">Reference article</a>
</article>`;
const fixtureCertificate = new X509Certificate(await readFile(certPath));
const fixtureSpki = createHash('sha256').update(fixtureCertificate.publicKey.export({ type: 'spki', format: 'der' })).digest('base64');
const server = createServer({ pfx: await readFile(pfxPath), passphrase: 'suriph-fixture' }, (_request, response) => {
  response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
  response.end(fixtureHtml);
});
await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
const fixturePort = server.address().port;

class CDP {
  constructor(url) { this.url = url; this.id = 0; this.pending = new Map(); }
  async open() {
    this.socket = new WebSocket(this.url);
    await new Promise((resolve, reject) => { this.socket.onopen = resolve; this.socket.onerror = reject; });
    this.socket.onmessage = event => {
      const message = JSON.parse(event.data);
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
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const targets = port => fetch(`http://127.0.0.1:${port}/json/list`).then(response => response.json());
async function evaluate(client, expression, awaitPromise = false) {
  const output = await client.send('Runtime.evaluate', { expression, awaitPromise, returnByValue: true, userGesture: true });
  if (output.exceptionDetails) throw new Error(output.exceptionDetails.exception?.description || output.exceptionDetails.text);
  return output.result?.value;
}
async function waitFor(client, expression, timeout = 180000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) { try { if (await evaluate(client, expression, true)) return; } catch {} await wait(100); }
  throw new Error(`Timed out waiting for ${expression}`);
}

const browser = spawn(BROWSER, [
  '--disable-gpu', '--no-sandbox', '--no-first-run', '--no-default-browser-check', '--window-size=1200,900', '--window-position=-32000,-32000',
  `--user-data-dir=${PROFILE}`, '--remote-debugging-port=0',
  '--host-resolver-rules=MAP www.facebook.com 127.0.0.1', `--ignore-certificate-errors-spki-list=${fixtureSpki}`, `--explicitly-allowed-ports=${fixturePort}`,
  `--disable-extensions-except=${EXTENSION}`, `--load-extension=${EXTENSION}`, `https://www.facebook.com:${fixturePort}/fixture`,
], { windowsHide: true, stdio: 'ignore' });
let page;
try {
  let port;
  for (let attempt = 0; attempt < 200 && !port; attempt++) { try { port = Number((await readFile(path.join(PROFILE, 'DevToolsActivePort'), 'utf8')).split(/\r?\n/)[0]); } catch { await wait(100); } }
  assert.ok(port, 'Browser remote debugging did not start');
  let pageTarget;
  for (let attempt = 0; attempt < 200 && !pageTarget; attempt++) {
    pageTarget = (await targets(port)).find(item => item.type === 'page' && item.url.includes('www.facebook.com'));
    await wait(100);
  }
  assert.ok(pageTarget, 'Facebook fixture page did not open');
  page = await new CDP(pageTarget.webSocketDebuggerUrl).open();
  await Promise.all([page.send('Page.enable'), page.send('Runtime.enable')]);
  await waitFor(page, `Boolean(document.querySelector('#suriph-control-host')?.shadowRoot)`, 30000);

  await evaluate(page, `document.querySelector('#suriph-control-host').shadowRoot.querySelector('.action').click(); true`);
  await waitFor(page, `document.querySelector('#suriph-control-host').shadowRoot.textContent.includes('Analyze this text')`);
  const previewText = await evaluate(page, `document.querySelector('#suriph-control-host').shadowRoot.querySelector('.result p').textContent`);
  assert.equal(previewText, 'BREAKING!!! Share agad!!! Totoo ba ito?');
  await evaluate(page, `(() => { const root=document.querySelector('#suriph-control-host').shadowRoot; const lookup=[...root.querySelectorAll('label')].find(node=>node.textContent.includes('Send up to 500 characters'))?.querySelector('input'); if(lookup?.checked) lookup.click(); [...root.querySelectorAll('button')].find(node=>node.textContent.includes('Analyze this text')).click(); return true; })()`);
  await waitFor(page, `document.querySelector('#suriph-control-host').shadowRoot.querySelectorAll('[data-result-part]').length===8`);

  const state = await evaluate(page, `(() => { const root=document.querySelector('#suriph-control-host').shadowRoot; const result=root.querySelector('.result'); const action=root.querySelector('.action'); return {parts:[...result.querySelectorAll('[data-result-part]')].map(node=>node.dataset.resultPart),buttonPart:action.dataset.resultPart,resultOrder:result.style.order,buttonOrder:action.style.order,label:result.querySelector('[data-result-part="1-prediction"]').textContent,score:result.querySelector('[data-result-part="2-score"] strong').textContent,analyzed:result.querySelector('[data-result-part="6-analyzed-text"] p:last-child').textContent,context:result.querySelector('[data-result-part="3-post-context"]').innerText,links:[...result.querySelectorAll('[data-result-part="3-post-context"] a')].map(node=>node.href),reminders:result.querySelectorAll('[data-result-part="7-reminder"]').length,sourceText:result.querySelector('[data-result-part="5-related-sources"]').innerText}; })()`);
  assert.deepEqual(state.parts, ['1-prediction', '2-score', '3-post-context', '4-features', '5-related-sources', '6-analyzed-text', '7-reminder']);
  assert.equal(state.buttonPart, '8-check-again');
  assert.equal(state.resultOrder, '2');
  assert.equal(state.buttonOrder, '3');
  assert.equal(state.analyzed, previewText);
  assert.match(state.context, /Researcher Fixture/);
  assert.match(state.context, /2026-10-20T08:00:00Z/);
  assert.match(state.context, /Facebook post caption/);
  assert.ok(state.links.some(url => url.includes('/posts/123')));
  assert.ok(state.links.includes('https://example.org/reference'));
  assert.equal(state.reminders, 1);
  assert.match(state.sourceText, /Source lookup was not requested/);

  const beforeLookup = { label: state.label, score: state.score, analyzed: state.analyzed };
  await evaluate(page, `(() => { const root=document.querySelector('#suriph-control-host').shadowRoot; [...root.querySelectorAll('button')].find(node=>node.textContent==='Find related sources').click(); return true; })()`);
  await waitFor(page, `!document.querySelector('#suriph-control-host').shadowRoot.textContent.includes('Finding related sources')`, 30000);
  const afterLookup = await evaluate(page, `(() => { const result=document.querySelector('#suriph-control-host').shadowRoot.querySelector('.result'); return {label:result.querySelector('[data-result-part="1-prediction"]').textContent,score:result.querySelector('[data-result-part="2-score"] strong').textContent,analyzed:result.querySelector('[data-result-part="6-analyzed-text"] p:last-child').textContent,sourceText:result.querySelector('[data-result-part="5-related-sources"]').innerText}; })()`);
  assert.deepEqual({ label: afterLookup.label, score: afterLookup.score, analyzed: afterLookup.analyzed }, beforeLookup);
  assert.doesNotMatch(afterLookup.sourceText, /Source lookup was not requested/);

  await evaluate(page, `(() => { const root=document.querySelector('#suriph-control-host').shadowRoot; [...root.querySelectorAll('button')].find(node=>node.textContent==='Tagalog').click(); return true; })()`);
  await waitFor(page, `document.querySelector('#suriph-control-host').shadowRoot.textContent.includes('Konteksto ng post')`);
  const tagalog = await evaluate(page, `(() => { const result=document.querySelector('#suriph-control-host').shadowRoot.querySelector('.result'); return {label:result.querySelector('[data-result-part="1-prediction"]').textContent,score:result.querySelector('[data-result-part="2-score"] strong').textContent,analyzed:result.querySelector('[data-result-part="6-analyzed-text"] p:last-child').textContent}; })()`);
  assert.deepEqual(tagalog, beforeLookup);

  const shot = await page.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  await writeFile(path.join(SHOTS, 'facebook-modal-synthetic.png'), Buffer.from(shot.data, 'base64'));
  const report = {
    passed: true,
    browser: path.basename(BROWSER).toLowerCase().includes('msedge') ? 'Microsoft Edge (isolated off-screen profile)' : 'Google Chrome (isolated off-screen profile)',
    unpacked_extension_loaded: true,
    manifest_supported_facebook_origin: true,
    bounded_caption_extraction: 'passed',
    exact_eight_part_visual_order: 'passed',
    post_author_timestamp_scope_and_links: 'passed',
    source_only_lookup_preserves_prediction: 'passed',
    bilingual_switch_preserves_label_score_and_text: 'passed',
    one_bottom_reminder: 'passed',
    actual_facebook_account_tested: false,
    fixture_note: 'Local HTTPS facebook.com fixture; no real account, post, message, or participant data was used.',
    screenshot_private: true,
  };
  await writeFile(path.join(ROOT, 'docs', 'FACEBOOK-MODAL-VERIFICATION.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
} finally {
  page?.close();
  server.close();
  if (process.platform === 'win32') spawnSync('taskkill', ['/PID', String(browser.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
  else browser.kill('SIGKILL');
}
