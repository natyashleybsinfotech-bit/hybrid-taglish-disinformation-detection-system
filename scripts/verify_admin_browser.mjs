// Real Chrome administrator-flow rehearsal against the running dashboard and API.
// The isolated profile, download and screenshots stay under ignored tmp/.
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { spawn, spawnSync } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const CHROME = process.env.SURI_TEST_BROWSER || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const RUN = path.join(ROOT, 'tmp', `admin-browser-${Date.now()}`);
const PROFILE = path.join(RUN, 'profile');
const SHOTS = path.join(RUN, 'screenshots');
await Promise.all([mkdir(PROFILE, { recursive: true }), mkdir(SHOTS, { recursive: true })]);

function envFile(file) {
  return Object.fromEntries(file.split(/\r?\n/).filter(line => line && !line.trimStart().startsWith('#') && line.includes('='))
    .map(line => { const index = line.indexOf('='); return [line.slice(0, index), line.slice(index + 1)]; }));
}
const privateEnv = envFile(await readFile(path.join(ROOT, 'backend-api', '.env.local'), 'utf8'));
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const keepAlive = setInterval(() => {}, 1000);

class CDP {
  constructor(url) { this.url = url; this.id = 0; this.pending = new Map(); }
  async open() {
    this.socket = new WebSocket(this.url);
    await new Promise((resolve, reject) => { this.socket.onopen = resolve; this.socket.onerror = reject; });
    this.socket.onmessage = event => {
      const message = JSON.parse(event.data);
      if (process.env.SURI_CDP_DEBUG === '1') console.error('admin-browser: cdp', String(event.data).slice(0, 300));
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

async function evaluate(client, expression, awaitPromise = false) {
  const output = await client.send('Runtime.evaluate', { expression, awaitPromise, returnByValue: true, userGesture: true });
  if (output.exceptionDetails) throw new Error(output.exceptionDetails.exception?.description || output.exceptionDetails.text);
  return output.result?.value;
}
async function waitFor(client, expression, timeout = 30000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) { try { if (await evaluate(client, expression, true)) return; } catch {} await wait(100); }
  throw new Error(`Timed out waiting for ${expression}`);
}
async function setControl(client, selector, value) {
  await evaluate(client, `(() => { const element=document.querySelector(${JSON.stringify(selector)}); const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; setter.call(element,${JSON.stringify(value)}); element.dispatchEvent(new Event('input',{bubbles:true})); return true; })()`);
}
async function clickText(client, text) {
  await evaluate(client, `(() => { const node=[...document.querySelectorAll('button,a')].find(item=>item.textContent.includes(${JSON.stringify(text)})); if(!node) throw new Error('Missing control'); node.click(); return true; })()`);
}
async function screenshot(client, name, width, height) {
  await client.send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
  const result = await client.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  await writeFile(path.join(SHOTS, `${name}.png`), Buffer.from(result.data, 'base64'));
}

const chrome = spawn(CHROME, [
  '--disable-gpu', '--no-sandbox', '--no-first-run', '--no-default-browser-check', '--window-position=-32000,-32000', '--window-size=400,400',
  `--user-data-dir=${PROFILE}`, '--remote-debugging-port=0', 'about:blank',
], { windowsHide: true, stdio: ['ignore', 'ignore', 'pipe'] });
let stderr = '';
chrome.stderr.on('data', chunk => { stderr += String(chunk); });
let port;
for (let attempt = 0; attempt < 200 && !port; attempt++) {
  port = Number(stderr.match(/DevTools listening on ws:\/\/127\.0\.0\.1:(\d+)/)?.[1] || 0);
  await wait(50);
}
assert.ok(port, 'Chrome DevTools endpoint did not start');
console.error('admin-browser: chrome started');
const created = (await fetch(`http://127.0.0.1:${port}/json/list`).then(response => response.json())).find(target => target.type === 'page');
assert.ok(created, 'Chrome page target did not start');
console.error(`admin-browser: target ${created.url} ${created.title}`);
const client = await new CDP(created.webSocketDebuggerUrl).open();
console.error('admin-browser: target connected');

try {
  await client.send('Page.navigate', { url: 'http://127.0.0.1:5173/' });
  await waitFor(client, 'Boolean(document.querySelector("input[autocomplete=username]"))');
  console.error('admin-browser: login loaded');
  const noHorizontalOverflow = await evaluate(client, 'document.documentElement.scrollWidth <= document.documentElement.clientWidth');
  assert.equal(noHorizontalOverflow, true);
  await screenshot(client, 'admin-login-actual', 1280, 900);
  await client.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
  await client.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
  const firstKeyboardTarget = await evaluate(client, 'document.activeElement?.getAttribute("autocomplete") || document.activeElement?.tagName');
  assert.equal(firstKeyboardTarget, 'username');

  await setControl(client, 'input[autocomplete=username]', privateEnv.SURI_ADMIN_USERNAME);
  await setControl(client, 'input[autocomplete=current-password]', privateEnv.SURI_ADMIN_PASSWORD);
  await clickText(client, 'Continue');
  await waitFor(client, 'document.body.innerText.includes("System status") && document.body.innerText.includes("Log out")');
  console.error('admin-browser: admin login passed');
  const loginPayloadHasToken = await evaluate(client, `fetch('http://127.0.0.1:8000/admin-api/check-auth',{credentials:'include'}).then(r=>r.json()).then(v=>Object.hasOwn(v,'token'))`, true);
  assert.equal(loginPayloadHasToken, false);
  await client.send('Page.reload', { ignoreCache: true });
  await waitFor(client, 'document.body.innerText.includes("Log out")');
  console.error('admin-browser: reload passed');
  const sessionReload = !(await evaluate(client, 'document.body.innerText')).includes('Enter your credentials');
  assert.equal(sessionReload, true);
  assert.equal((await evaluate(client, 'document.body.innerText')).includes('Participant research'), false);
  await evaluate(client, 'history.pushState({},"","/research"); window.dispatchEvent(new PopStateEvent("popstate")); true');
  await waitFor(client, 'location.pathname==="/"');
  const retiredExport = await evaluate(client, `fetch('http://127.0.0.1:8000/admin-api/research-export',{credentials:'include'}).then(r=>r.status)`, true);
  assert.equal(retiredExport, 404);
  await clickText(client, 'Log out');
  await waitFor(client, 'document.body.innerText.includes("Enter your credentials")');
  console.error('admin-browser: admin logout passed');
  const afterLogout = await evaluate(client, `fetch('http://127.0.0.1:8000/admin-api/check-auth',{credentials:'include'}).then(r=>r.status)`, true);
  assert.equal(afterLogout, 401);

  await setControl(client, 'input[autocomplete=username]', privateEnv.SURI_VIEWER_USERNAME);
  await setControl(client, 'input[autocomplete=current-password]', privateEnv.SURI_VIEWER_PASSWORD);
  await clickText(client, 'Continue');
  await waitFor(client, 'document.body.innerText.includes("view only")');
  console.error('admin-browser: viewer login passed');
  assert.equal((await evaluate(client, 'document.body.innerText')).includes('Participant research'), false);

  const payload = Buffer.from(JSON.stringify({ username: 'expired-fixture', role: 'admin', expires: 1 })).toString('base64url');
  const signature = createHmac('sha256', privateEnv.SURI_SESSION_SECRET).update(payload).digest('hex');
  const expired = await fetch('http://127.0.0.1:8000/admin-api/check-auth', { headers: { Cookie: `suriph_admin_token=${payload}.${signature}` } }).then(response => response.status);
  assert.equal(expired, 401);
  await screenshot(client, 'admin-viewer-narrow-actual', 390, 844);
  const narrowOverflow = await evaluate(client, 'document.documentElement.scrollWidth <= document.documentElement.clientWidth');
  assert.equal(narrowOverflow, true);

  const report = {
    passed: true,
    browser: `${path.basename(CHROME).toLowerCase().includes('msedge') ? 'Microsoft Edge' : 'Google Chrome'} (isolated off-screen profile)`,
    actual_dashboard_and_api: true,
    admin_login: 'passed', session_cookie_reload: 'passed', login_json_exposes_token: false,
    logout_revocation_status: afterLogout, participant_view_absent: 'passed', retired_research_export_status: retiredExport,
    expired_session_status: expired,
    keyboard_first_target: firstKeyboardTarget, desktop_no_horizontal_overflow: noHorizontalOverflow,
    narrow_no_horizontal_overflow: narrowOverflow,
    screenshots_private: true,
    limitations: ['Automated Chrome is not a screen-reader test.', 'No participant data was created or changed.'],
  };
  await writeFile(path.join(ROOT, 'docs', 'ADMIN-BROWSER-VERIFICATION.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
} finally {
  clearInterval(keepAlive);
  client.close();
  if (process.platform === 'win32') spawnSync('taskkill', ['/PID', String(chrome.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
  else chrome.kill('SIGKILL');
  chrome.stderr.destroy();
  chrome.unref();
}
