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

const certPath = process.env.SURI_TEST_CERT_CER || path.join(RUN, 'fixture.cer');
const pfxPath = process.env.SURI_TEST_CERT_PFX || path.join(RUN, 'fixture.pfx');
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
const powershell = process.env.SURI_TEST_POWERSHELL || path.join(process.env.SystemRoot || 'C:/Windows', 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe');
if (!process.env.SURI_TEST_CERT_CER || !process.env.SURI_TEST_CERT_PFX) {
  const certificate = spawnSync(powershell, ['-NoProfile', '-Command', certificateScript], {
    windowsHide: true, encoding: 'utf8', env: { ...process.env, SURI_CERT_OUT: certPath, SURI_PFX_OUT: pfxPath },
  });
  assert.equal(certificate.status, 0, `Could not create fixture certificate: ${certificate.error?.message || certificate.stderr}`);
}

const fixtureHtml = `<!doctype html><meta charset="utf-8"><title>SuriPH Facebook fixture</title><main role="main">
<article id="target-post" role="article" tabindex="0">
  <h2><a role="link" href="https://www.facebook.com/researcher.fixture">Researcher Fixture</a></h2>
  <div data-ad-comet-preview="message"><div>BREAKING!!! Share agad!!! Totoo ba ito?</div><span role="button" aria-expanded="true" tabindex="0">See more</span><div>User wrote &quot;See less&quot; in the caption.</div></div>
  <button type="button">Unrelated post menu</button>
  <div aria-label="Reactions and actions">999 reactions Like Comment Share</div>
  <article role="article"><p>Unrelated nested comment Reply 47</p><button>Reply</button><a href="https://example.org/comment-only">Comment link</a><time datetime="2001-01-01">Old comment date</time></article>
  <time datetime="2026-10-20T08:00:00Z">October 20 at 4:00 PM</time>
  <a href="https://www.facebook.com/researcher.fixture/posts/123">Original post</a>
  <a href="https://example.org/reference">Reference article</a>
</article>
<article id="neighbor-post" role="article" tabindex="0">
  <h2><a role="link" href="https://www.facebook.com/neighbor.fixture">Neighbor post</a></h2><time datetime="2026-10-20T10:00:00Z">October 20</time>
  <p>Unrecognized plain text must fail closed and never be submitted.</p>
  <button type="button">Like</button>
</article>
<article id="second-post" role="article" tabindex="0"><h2><a role="link" href="https://www.facebook.com/second.fixture">Second Fixture</a></h2><div data-ad-comet-preview="message">The city office opened a new public library on October 20, 2026.</div><a href="https://www.facebook.com/second.fixture/posts/456" aria-label="November 13, 2026 at 8:00 PM">1d</a></article>
<article id="image-post" role="article" tabindex="0"><h2><a role="link" href="https://www.facebook.com/image.fixture">Image Fixture</a></h2><time datetime="2026-10-20T09:00:00Z">October 20</time><div data-ad-comet-preview="message">The House has approved the proposed measure on second reading.</div><div role="article"><a href="https://www.facebook.com/photo/?fbid=fixture"><img src="/own-photo.png" width="700" height="580" style="width:700px;height:580px" alt="Anti-grooming bill advances in House"></a></div><article role="article" aria-label="Comment by another person"><div data-ad-comet-preview="message">A different person's comment must be excluded.</div><button>Reply</button><img src="/comment-photo.png" width="900" height="700" style="width:900px;height:700px"></article></article>
<article id="media-post" role="article" tabindex="0"><h2><a role="link" href="https://www.facebook.com/media.fixture">Media Fixture</a></h2><time datetime="2026-10-20T09:00:00Z">October 20</time><div data-ad-comet-preview="message">A short public video caption for the chooser preview.</div><video muted width="200" height="120" src="https://www.facebook.com/main-video"></video><article role="article" aria-label="Comment by another person"><button>Reply</button><video muted width="900" height="600" src="https://www.facebook.com/comment-video"></video></article></article></main>`;
const fixtureCertificate = new X509Certificate(await readFile(certPath));
const fixtureSpki = createHash('sha256').update(fixtureCertificate.publicKey.export({ type: 'spki', format: 'der' })).digest('base64');
const server = createServer({ pfx: await readFile(pfxPath), passphrase: 'suriph-fixture' }, (_request, response) => {
  if (_request.url.endsWith('.png')) {
    response.writeHead(200, { 'Content-Type': 'image/png' });
    response.end(Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l1sAAAAASUVORK5CYII=', 'base64')); return;
  }
  response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
  response.end(fixtureHtml);
});
await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
const fixturePort = server.address().port;

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
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const targets = port => fetch(`http://127.0.0.1:${port}/json/list`).then(response => response.json());
async function evaluate(client, expression, awaitPromise = false) {
  const output = await client.send('Runtime.evaluate', { expression, awaitPromise, returnByValue: true, userGesture: true });
  if (output.exceptionDetails) throw new Error(output.exceptionDetails.exception?.description || output.exceptionDetails.text);
  return output.result?.value;
}
async function waitFor(client, expression, timeout = 60000) {
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
  page.listeners.push(message => {
    if (message.method === 'Runtime.exceptionThrown') console.error('Fixture exception', JSON.stringify(message.params.exceptionDetails?.exception?.description || message.params.exceptionDetails?.text));
    if (message.method === 'Runtime.consoleAPICalled' && message.params.type === 'error') console.error('Fixture console error', JSON.stringify(message.params.args?.map(item => item.description || item.value)));
  });
  await page.send('Page.reload', { ignoreCache: true });
  await wait(500);
  await waitFor(page, `Boolean(document.querySelector('#target-post > #suriph-control-host')?.shadowRoot)`, 30000);
  await waitFor(page, `Boolean(document.querySelector('#media-post > #suriph-control-host')?.shadowRoot)`, 30000);
  await evaluate(page, `document.querySelector('#media-post > #suriph-control-host').shadowRoot.querySelector('.action').click(); true`);
  await waitFor(page, `document.querySelector('body > dialog > #suriph-control-host')?.shadowRoot.textContent.includes('Check this video')`);
  const openLayout = await evaluate(page, `(() => { const dialog=document.querySelector('body > dialog'); const wrap=dialog.querySelector('#suriph-control-host').shadowRoot.querySelector('.wrap'); return {dialogWidth:dialog.getBoundingClientRect().width,wrapWidth:wrap.getBoundingClientRect().width,expanded:wrap.classList.contains('expanded')}; })()`);
  assert.ok(openLayout.expanded && openLayout.wrapWidth >= 320, `Modal collapsed when open: ${JSON.stringify(openLayout)}`);
  assert.equal(await evaluate(page, `document.querySelector('#target-post > #suriph-control-host').style.visibility`), 'hidden', 'Other S controls must not bleed through the chooser');
  const chooserShot = await page.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  await writeFile(path.join(SHOTS, 'facebook-modal-chooser.png'), Buffer.from(chooserShot.data, 'base64'));
  await evaluate(page, `document.querySelector('body > dialog > #suriph-control-host').shadowRoot.querySelector('.close').click(); true`);
  const closedLayout = await evaluate(page, `(() => { const host=document.querySelector('#media-post > #suriph-control-host'); const root=host.shadowRoot; return {wrapWidth:root.querySelector('.wrap').getBoundingClientRect().width,resultDisplay:getComputedStyle(root.querySelector('.result')).display,resultHeight:root.querySelector('.result').getBoundingClientRect().height}; })()`);
  assert.equal(closedLayout.resultDisplay, 'none', `Closed result remained visible: ${JSON.stringify(closedLayout)}`);
  assert.equal(closedLayout.resultHeight, 0);
  assert.equal(await evaluate(page, `document.querySelector('#target-post > #suriph-control-host').style.visibility`), '', 'Other S controls must return after closing the chooser');

  const directVideoRequests = [];
  const mediaWorkerTarget = (await targets(port)).find(item => item.type === 'service_worker' && item.url.endsWith('/service-worker-loader.js'));
  assert.ok(mediaWorkerTarget, 'The extension background worker must handle direct video fetch');
  const mediaWorker = await new CDP(mediaWorkerTarget.webSocketDebuggerUrl).open();
  await mediaWorker.send('Network.enable');
  mediaWorker.listeners.push(message => {
    if (message.method === 'Network.requestWillBeSent'
        && /\/(?:main|comment)-video$/.test(message.params.request.url)) directVideoRequests.push(message.params.request.url);
  });
  await evaluate(page, `document.querySelector('#media-post > #suriph-control-host').shadowRoot.querySelector('.action').click(); true`);
  await waitFor(page, `document.querySelector('body > dialog > #suriph-control-host')?.shadowRoot.textContent.includes('Check this video')`);
  await evaluate(page, `(() => { const root=document.querySelector('body > dialog > #suriph-control-host').shadowRoot; [...root.querySelectorAll('button')].find(node=>node.textContent.includes('Check this video')).click(); return true; })()`);
  for (let attempt=0; attempt<100 && !directVideoRequests.length; attempt++) await wait(100);
  assert.deepEqual(directVideoRequests, ['https://www.facebook.com/main-video']);
  await waitFor(page, `document.querySelector('body > dialog > #suriph-control-host')?.shadowRoot.querySelector('.message[data-tone="error"]')?.textContent.includes('video')`, 15000);
  const unavailableVideoState = await evaluate(page, `document.querySelector('body > dialog > #suriph-control-host').shadowRoot.querySelector('.result').textContent`);
  assert.doesNotMatch(unavailableVideoState, /No Misleading Information Detected|Potentially Misleading/);
  mediaWorker.close();
  await evaluate(page, `document.querySelector('body > dialog > #suriph-control-host').shadowRoot.querySelector('.close').click(); true`);

  await waitFor(page, `Boolean(document.querySelector('#image-post > #suriph-control-host')?.shadowRoot)`);
  await evaluate(page, `document.querySelector('#image-post > #suriph-control-host').shadowRoot.querySelector('.action').click(); true`);
  await waitFor(page, `document.querySelector('body > dialog > #suriph-control-host')?.shadowRoot.textContent.includes('Check this image')`);
  assert.equal(await evaluate(page, `document.querySelector('body > dialog > #suriph-control-host').shadowRoot.textContent.includes('Analyze this text')`), false, 'Own photo must produce the media chooser, not silently choose the caption');
  await evaluate(page, `(() => { const root=document.querySelector('body > dialog > #suriph-control-host').shadowRoot; [...root.querySelectorAll('button')].find(node=>node.textContent.includes('Check caption/text')).click(); return true; })()`);
  await waitFor(page, `document.querySelector('body > dialog > #suriph-control-host').shadowRoot.textContent.includes('Analyze this text')`);
  const imageCaption = await evaluate(page, `document.querySelector('body > dialog > #suriph-control-host').shadowRoot.querySelector('.result p').textContent`);
  assert.equal(imageCaption, 'The House has approved the proposed measure on second reading.');
  await evaluate(page, `document.querySelector('body > dialog > #suriph-control-host').shadowRoot.querySelector('.close').click(); true`);

  assert.equal(await evaluate(page, `Boolean(document.querySelector('#neighbor-post > #suriph-control-host'))`), false,
    'A container without a readable caption or media must not expose a screening control');
  await evaluate(page, `document.querySelector('#target-post > #suriph-control-host').shadowRoot.querySelector('.action').click(); true`);
  const postClickState = await evaluate(page, `new Promise(resolve => setTimeout(() => { const host=document.querySelector('body > dialog > #suriph-control-host'); resolve({postText:document.querySelector('#target-post').innerText,shadowText:host.shadowRoot.textContent,shadowHtml:host.shadowRoot.innerHTML.slice(0,1200)}); }, 250))`, true);
  if (!postClickState.shadowText.includes('Analyze this text')) console.error(JSON.stringify(postClickState, null, 2));
  await waitFor(page, `document.querySelector('body > dialog > #suriph-control-host').shadowRoot.textContent.includes('Analyze this text')`);
  const previewText = await evaluate(page, `document.querySelector('body > dialog > #suriph-control-host').shadowRoot.querySelector('.result p').textContent`);
  assert.equal(previewText, 'BREAKING!!! Share agad!!! Totoo ba ito? User wrote "See less" in the caption.');
  assert.ok(!previewText.includes('ito?User'), 'Block boundaries must not collapse adjacent caption sections');
  assert.doesNotMatch(previewText, /See more/);
  assert.match(previewText, /See less/, 'User-authored control-like words must be preserved');
  assert.doesNotMatch(previewText, /menu|reaction|comment|reply|neighbor/i);
  const reviewShot = await page.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  await writeFile(path.join(SHOTS, 'facebook-modal-review.png'), Buffer.from(reviewShot.data, 'base64'));

  await evaluate(page, `(() => { const root=document.querySelector('body > dialog > #suriph-control-host').shadowRoot; const lookup=root.querySelector('.lookup-choice input'); if(lookup?.checked) lookup.click(); [...root.querySelectorAll('button')].find(node=>node.textContent.includes('Analyze this text')).click(); return true; })()`);
  await waitFor(page, `document.querySelector('body > dialog > #suriph-control-host').shadowRoot.querySelectorAll('[data-result-part]').length===8`);

  const state = await evaluate(page, `(() => { const root=document.querySelector('body > dialog > #suriph-control-host').shadowRoot; const result=root.querySelector('.result'); const action=root.querySelector('.action'); return {parts:[...result.querySelectorAll('[data-result-part]')].map(node=>node.dataset.resultPart),buttonPart:action.dataset.resultPart,resultOrder:result.style.order,buttonOrder:action.style.order,label:result.querySelector('[data-result-part="1-prediction"] strong').textContent,analyzed:result.querySelector('[data-result-part="6-analyzed-text"] p:last-child').textContent,context:result.querySelector('[data-result-part="3-post-context"]').innerText,links:[...result.querySelectorAll('[data-result-part="3-post-context"] a')].map(node=>node.href),reminders:result.querySelectorAll('[data-result-part="7-reminder"]').length,sourceText:result.querySelector('[data-result-part="5-related-sources"]').innerText}; })()`);
  assert.deepEqual(state.parts, ['1-prediction', '2-explanation', '3-post-context', '4-features', '5-related-sources', '6-analyzed-text', '7-reminder']);
  assert.equal(state.buttonPart, '8-check-again');
  const measuredFeatures = await evaluate(page, `(() => { const result=document.querySelector('body > dialog > #suriph-control-host').shadowRoot.querySelector('.result'); const detail=result.querySelector('[data-result-part="4-features"]'); detail.querySelector('summary').click(); const rows=[...detail.querySelectorAll('[data-feature]')]; return {open:detail.open,count:rows.length,uniqueNames:new Set(rows.map(row=>row.dataset.feature)).size,valuesFinite:rows.every(row=>Number.isFinite(Number(row.dataset.value))&&Number(row.dataset.value)>=0&&Number(row.dataset.value)<=1)}; })()`);
  assert.equal(measuredFeatures.count,7); assert.equal(measuredFeatures.open,true); assert.equal(measuredFeatures.uniqueNames,7); assert.equal(measuredFeatures.valuesFinite,true);

  const scorePresentation = await evaluate(page, `(() => { const root=document.querySelector('body > dialog > #suriph-control-host').shadowRoot; const result=root.querySelector('.result'); return {score:result.querySelector('.ai-score')?.innerText||'',text:result.innerText,explanation:[...result.querySelector('[data-result-part="2-explanation"]').children].filter(n=>n.tagName==='P').map(n=>n.textContent).join(' ')}; })()`);
  assert.doesNotMatch(scorePresentation.text, /Google Gemini|Google Search/);
  if(scorePresentation.score) { assert.match(scorePresentation.score, /AI-reported confidence/); assert.match(scorePresentation.score, /\d+%/); assert.ok(scorePresentation.explanation.length>10); }

  assert.ok(['Potentially Misleading', 'No Misleading Information Detected'].includes(state.label), `Unexpected public label: ${state.label}`);
  assert.equal(state.resultOrder, '2');
  assert.equal(state.buttonOrder, '3');
  assert.equal(state.analyzed, previewText);
  assert.match(state.context, /Researcher Fixture/);
  assert.match(state.context, /Oct 20, 2026/);
  assert.match(state.context, /How recent:/);
  assert.match(state.context, /Content checked: Post caption/);
  assert.ok(state.links.some(url => url.includes('/posts/123')));
  assert.ok(!state.links.includes('https://example.org/comment-only'), 'Nested comment links must not become post context');
  assert.equal(state.reminders, 1);
  assert.match(state.sourceText, /Source search was not requested/);

  const beforeLookup = { label: state.label, analyzed: state.analyzed };
  await evaluate(page, `(() => { const root=document.querySelector('body > dialog > #suriph-control-host').shadowRoot; [...root.querySelectorAll('button')].find(node=>node.textContent==='Find related sources').click(); return true; })()`);
  await waitFor(page, `!document.querySelector('body > dialog > #suriph-control-host').shadowRoot.textContent.includes('Finding related sources')`, 30000);
  const afterLookup = await evaluate(page, `(() => { const result=document.querySelector('body > dialog > #suriph-control-host').shadowRoot.querySelector('.result'); return {label:result.querySelector('[data-result-part="1-prediction"] strong').textContent,analyzed:result.querySelector('[data-result-part="6-analyzed-text"] p:last-child').textContent,sourceText:result.querySelector('[data-result-part="5-related-sources"]').innerText}; })()`);
  assert.deepEqual({ label: afterLookup.label, analyzed: afterLookup.analyzed }, beforeLookup);
  assert.doesNotMatch(afterLookup.sourceText, /Source search was not requested/);

  await evaluate(page, `(() => { const root=document.querySelector('body > dialog > #suriph-control-host').shadowRoot; [...root.querySelectorAll('button')].find(node=>node.textContent==='Tagalog').click(); return true; })()`);
  await waitFor(page, `document.querySelector('body > dialog > #suriph-control-host').shadowRoot.textContent.includes('Tungkol sa post')`);
  const tagalog = await evaluate(page, `(() => { const result=document.querySelector('body > dialog > #suriph-control-host').shadowRoot.querySelector('.result'); return {label:result.querySelector('[data-result-part="1-prediction"] strong').textContent,analyzed:result.querySelector('[data-result-part="6-analyzed-text"] p:last-child').textContent}; })()`);
  assert.deepEqual(tagalog, beforeLookup);

  const shot = await page.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  await writeFile(path.join(SHOTS, 'facebook-modal-synthetic.png'), Buffer.from(shot.data, 'base64'));
  await evaluate(page, `document.querySelector('body > dialog > #suriph-control-host').shadowRoot.querySelector('.wrap.expanded').scrollTop = 99999; true`);
  const bottomShot = await page.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  await writeFile(path.join(SHOTS, 'facebook-modal-result-bottom.png'), Buffer.from(bottomShot.data, 'base64'));
  await evaluate(page, `(() => { const root=document.querySelector('body > dialog > #suriph-control-host').shadowRoot; [...root.querySelectorAll('.language-switch button')].find(node=>node.textContent==='English').click(); return true; })()`);
  await evaluate(page, `document.querySelector('body > dialog > #suriph-control-host').shadowRoot.querySelector('.close').click(); true`);
  const closedResult = await evaluate(page, `(() => { const host=document.querySelector('#target-post > #suriph-control-host'); const root=host.shadowRoot; const result=root.querySelector('.result'); return {collapsed:!root.querySelector('.wrap').classList.contains('expanded'),hidden:result.hidden,display:getComputedStyle(result).display,height:result.getBoundingClientRect().height}; })()`);
  assert.deepEqual(closedResult, { collapsed: true, hidden: true, display: 'none', height: 0 },
    `Closing a result must not leave its content in the 38px control: ${JSON.stringify(closedResult)}`);
  await evaluate(page, `(() => { const host=document.querySelector('#target-post > #suriph-control-host'); document.querySelector('#target-post [data-ad-comet-preview="message"]').replaceChildren(document.createTextNode('HINDI KAILANGANG I-CONFINE...')); host.shadowRoot.querySelector('.action').click(); return true; })()`);
  const incompleteState = await evaluate(page, `new Promise(resolve => setTimeout(() => resolve(document.querySelector('body > dialog > #suriph-control-host').shadowRoot.textContent), 100))`, true);
  assert.match(incompleteState, /caption looks incomplete/i);
  assert.doesNotMatch(incompleteState, /No Misleading Information Detected|Potentially Misleading/);
  await evaluate(page, `(() => { const first=document.querySelector('body > dialog > #suriph-control-host'); first.shadowRoot.querySelector('.close').click(); document.querySelector('#target-post [data-ad-comet-preview="message"]').textContent='The first office opened a new public library on October 19, 2026.'; first.shadowRoot.querySelector('.action').click(); first.shadowRoot.querySelector('.result button:last-child').click(); const second=document.querySelector('#second-post > #suriph-control-host'); second.shadowRoot.querySelector('.action').click(); return true; })()`);
  await waitFor(page, `document.querySelector('body > dialog > #suriph-control-host')?.shadowRoot.querySelector('.result p')?.textContent.includes('The city office opened')`);
  const switched = await evaluate(page, `(() => { const host=document.querySelector('body > dialog > #suriph-control-host'); return {owner:host.shadowRoot.textContent,preview:host.shadowRoot.querySelector('.result p')?.textContent}; })()`);
  assert.equal(switched.preview, 'The city office opened a new public library on October 20, 2026.');
  assert.doesNotMatch(switched.owner, /The first office opened/);
  await evaluate(page, `(() => { const root=document.querySelector('body > dialog > #suriph-control-host').shadowRoot; const lookup=root.querySelector('.lookup-choice input'); if (lookup?.checked) lookup.click(); [...root.querySelectorAll('button')].find(node=>node.textContent.includes('Analyze this text')).click(); return true; })()`);
  await waitFor(page, `document.querySelector('body > dialog > #suriph-control-host')?.shadowRoot.querySelector('[data-result-part="3-post-context"]')?.textContent.includes('Post date:')`);
  const linkDateContext = await evaluate(page, `document.querySelector('body > dialog > #suriph-control-host').shadowRoot.querySelector('[data-result-part="3-post-context"]').innerText`);
  assert.match(linkDateContext, /Nov 13, 2026/);
  assert.match(linkDateContext, /How recent:/);
  assert.doesNotMatch(linkDateContext, /How recent: Could not determine/);
  await evaluate(page, `document.querySelector('body > dialog > #suriph-control-host').shadowRoot.querySelector('.close').click(); true`);
  const workerTargets = (await targets(port)).filter(item => item.type === 'service_worker' && item.url.startsWith('chrome-extension://'));
  const workerTarget = workerTargets.find(item => item.url.endsWith('/service-worker-loader.js'));
  assert.ok(workerTarget, 'Extension service worker must be available for the reload regression');
  const worker = await new CDP(workerTarget.webSocketDebuggerUrl).open();
  await worker.send('Runtime.enable');
  const beforeReload = await evaluate(page, 'performance.timeOrigin');
  await Promise.race([worker.send('Runtime.evaluate', { expression: 'chrome.runtime.reload()' }).catch(() => {}), wait(1000)]);
  worker.close();
  await wait(500);
  await evaluate(page, `document.querySelector('#second-post > #suriph-control-host').shadowRoot.querySelector('.action').click(); true`);
  await waitFor(page, `performance.timeOrigin > ${beforeReload}`, 30000);
  await waitFor(page, `Boolean(document.querySelector('#target-post > #suriph-control-host')?.shadowRoot)`, 30000);
  const report = {
    passed: true,
    extension_version: JSON.parse(await readFile(path.join(EXTENSION, 'manifest.json'), 'utf8')).version,
    browser: path.basename(BROWSER).toLowerCase().includes('msedge') ? 'Microsoft Edge (isolated off-screen profile)' : 'Google Chrome (isolated off-screen profile)',
    unpacked_extension_loaded: true,
    manifest_supported_facebook_origin: true,
    bounded_caption_extraction: 'passed',
    chooser_isolates_other_controls: 'passed',
    actual_caption_control_removed_user_phrase_preserved: 'passed',
    menus_reactions_nested_comments_excluded: 'passed',
    nested_comment_caption_excluded: 'passed',
    neighboring_post_excluded: 'passed',
    nested_comment_video_and_context_links_excluded: 'passed',
    own_photo_inside_nested_article_exposes_image_choice: 'passed',
    direct_video_fetch_attempts_selected_media_only: 'passed',
    direct_fetch_failure_falls_back_without_prediction: 'passed',
    switching_posts_during_analysis: 'passed',
    stale_tab_refresh_after_extension_reload: 'passed',
    unrecognized_container_has_no_control: 'passed',
    incomplete_caption_no_prediction: 'passed',
    closed_result_has_zero_visible_content: 'passed',
    expanded_modal_has_usable_width: 'passed',
    exact_eight_part_visual_order: 'passed',
    post_author_timestamp_scope_and_links: 'passed',
    permalink_timestamp_without_time_element: 'passed',
    source_only_lookup_preserves_prediction: 'passed',
    bilingual_switch_preserves_label_and_text: 'passed',
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
