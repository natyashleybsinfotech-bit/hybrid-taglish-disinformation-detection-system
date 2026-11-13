// Replay an original local clip through Chromium's captureStream/MediaRecorder.
// Private diagnostic: does not submit the video or invoke the classifier.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const source = path.resolve(process.argv[2] || '');
const output = path.resolve(process.argv[3] || '');
if (!process.argv[2] || !process.argv[3]) throw new Error('Usage: node scripts/audit_video_capture.mjs source.mp4 captured.webm');
const bytes = await readFile(source);
await mkdir(path.dirname(output), { recursive: true });
const server = createServer((request, response) => {
  if (process.env.SURI_CAPTURE_DEBUG === '1') console.error('fixture request', request.url, request.headers.range || '');
  if (request.url === '/video.mp4') {
    const range = /^bytes=(\d+)-(\d*)$/.exec(request.headers.range || '');
    const start = range ? Number(range[1]) : 0;
    const end = range && range[2] ? Math.min(Number(range[2]), bytes.length - 1) : bytes.length - 1;
    response.writeHead(range ? 206 : 200, {
      'Content-Type': 'video/mp4', 'Accept-Ranges': 'bytes', 'Content-Length': end - start + 1,
      ...(range ? { 'Content-Range': `bytes ${start}-${end}/${bytes.length}` } : {}),
    });
    response.end(bytes.subarray(start, end + 1));
    return;
  }
  response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
  response.end('<!doctype html><video id="source" src="/video.mp4" preload="auto" controls></video>');
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const port = server.address().port;
const profile = path.join(path.dirname(output), `capture-browser-profile-${Date.now()}`);
await mkdir(profile, { recursive: true });
const browser = spawn(process.env.SURI_TEST_BROWSER || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', [
  '--disable-gpu', '--no-sandbox', '--no-first-run', '--no-default-browser-check',
  '--autoplay-policy=no-user-gesture-required', '--disable-background-timer-throttling',
  '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows',
  '--window-size=800,600', '--window-position=-32000,-32000', `--user-data-dir=${profile}`,
  '--remote-debugging-port=0', `http://127.0.0.1:${port}/`,
], { windowsHide: true, stdio: 'ignore' });

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

let page;
try {
  let debugPort;
  for (let attempt = 0; attempt < 100 && !debugPort; attempt++) {
    try { debugPort = Number((await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split(/\r?\n/)[0]); }
    catch { await new Promise(resolve => setTimeout(resolve, 100)); }
  }
  assert.ok(debugPort, 'The isolated browser did not start');
  const targets = await fetch(`http://127.0.0.1:${debugPort}/json/list`).then(response => response.json());
  const target = targets.find(item => item.type === 'page' && item.url.includes(`127.0.0.1:${port}`));
  assert.ok(target, 'The local video page did not load');
  page = await new CDP(target.webSocketDebuggerUrl).open();
  await page.send('Runtime.enable');
  let ready = false;
  for (let attempt = 0; attempt < 100 && !ready; attempt++) {
    const observed = await page.send('Runtime.evaluate', { expression: "Boolean(document.querySelector('#source'))", returnByValue: true });
    ready = observed.result?.value === true;
    if (!ready) await new Promise(resolve => setTimeout(resolve, 100));
  }
  assert.ok(ready, 'The local video element did not load');
  const captureCode = (await readFile(path.resolve('chrome-extension/src/video_capture.js'), 'utf8')).replace('export async function', 'async function');
  const expression = captureCode + String.raw`(async () => {
    const video = document.querySelector('#source');
    const sourceFile = await fetch('/video.mp4').then(response => { if (!response.ok) throw new Error('Source video fetch failed'); return response.blob(); });
    video.src = URL.createObjectURL(sourceFile);
    video.load();
    if (video.readyState < 1) await Promise.race([
      new Promise(resolve => video.addEventListener('loadedmetadata', resolve, {once:true})),
      new Promise((_, reject) => setTimeout(() => reject(new Error('Video metadata timed out: networkState='+video.networkState+' error='+video.error?.code+' sourceBytes='+sourceFile.size+' canPlay='+video.canPlayType('video/mp4; codecs="avc1.4D401E, mp4a.40.5"'))), 15000)),
    ]);
    video.currentTime = Math.min(20, video.duration / 3);
    await new Promise(resolve => video.addEventListener('seeked', resolve, {once:true}));
    video.playbackRate = 1.5;
    const blob = await captureVideoElement(video);
    if (video.playbackRate !== 1.5) throw new Error('Playback rate was not restored');
    const audioTracks = 1; // Production capture rejects an absent audio track.
    const buffer = new Uint8Array(await blob.arrayBuffer());
    let binary = ''; for (let index=0; index<buffer.length; index+=0x8000) binary += String.fromCharCode(...buffer.subarray(index,index+0x8000));
    return {duration:video.duration, audioTracks, bytes:blob.size, base64:btoa(binary)};
  })()`;
  const result = await page.send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true, userGesture: true });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
  const value = result.result?.value;
  assert.ok(value?.bytes > 0, 'The capture was empty');
  await writeFile(output, Buffer.from(value.base64, 'base64'));
  console.log(JSON.stringify({ original_seconds: value.duration, captured_bytes: value.bytes, audio_tracks: value.audioTracks, output }));
} finally {
  page?.close(); browser.kill(); server.close();
}
