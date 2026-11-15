import test from 'node:test';
import assert from 'node:assert/strict';
import { captureVideoElement } from '../src/video_capture.js';

class Video extends EventTarget {
  duration = 2; currentTime = 0; playbackRate = 2; currentSrc = 'blob:selected';
  isConnected = true; paused = true; ended = false;
  tracks = [{ stop() {} }, { stop() {} }];
  captureStream() { return { getAudioTracks: () => [this.tracks[0]], getVideoTracks: () => [this.tracks[1]], getTracks: () => this.tracks }; }
  pause() { this.paused = true; }
  async play() { this.paused = false; }
}
class Recorder {
  state = 'inactive';
  start() { this.state = 'recording'; }
  stop() { this.state = 'inactive'; this.ondataavailable({ data: new Blob(['recorded media']) }); this.onstop(); }
}
globalThis.MediaRecorder = Recorder;

test('recording uses normal speed, completes only at the end and restores speed', async t => {
  t.mock.timers.enable({ apis: ['setTimeout', 'setInterval'] });
  const video = new Video(); const task = captureVideoElement(video);
  await Promise.resolve(); await Promise.resolve();
  assert.equal(video.playbackRate, 1);
  video.currentTime = 2; video.ended = true; video.dispatchEvent(new Event('ended'));
  const blob = await task;
  assert.ok(blob.size > 0); assert.equal(video.playbackRate, 2); assert.equal(video.paused, true);
});

test('stalled capture timeout rejects rather than uploading a partial clip', async t => {
  t.mock.timers.enable({ apis: ['setTimeout', 'setInterval'] });
  const video = new Video(); const task = captureVideoElement(video);
  const rejected = assert.rejects(task, /No partial video was submitted/);
  await Promise.resolve(); await Promise.resolve();
  t.mock.timers.tick(12001); await rejected;
  assert.equal(video.playbackRate, 2);
});

test('changed source aborts the recording of the selected post', async t => {
  t.mock.timers.enable({ apis: ['setTimeout', 'setInterval'] });
  const video = new Video(); const task = captureVideoElement(video);
  const rejected = assert.rejects(task, /selected video changed/);
  await Promise.resolve(); await Promise.resolve();
  video.currentSrc = 'blob:neighbor'; t.mock.timers.tick(100); await rejected;
});

test('skipping to the end cannot masquerade as a complete audio recording', async t => {
  t.mock.timers.enable({ apis: ['setTimeout', 'setInterval'] });
  const video = new Video(); const task = captureVideoElement(video);
  const rejected = assert.rejects(task, /seeked during capture/);
  await Promise.resolve(); await Promise.resolve();
  video.currentTime = video.duration; video.dispatchEvent(new Event('seeking'));
  await rejected;
});

test('closing or replacing the request stops capture and restores playback options', async t => {
  t.mock.timers.enable({ apis: ['setTimeout', 'setInterval'] });
  const video = new Video(); video.loop = true; video.autoplay = true;
  let current = true;
  const task = captureVideoElement(video, { shouldContinue: () => current });
  const rejected = assert.rejects(task, /cancelled/);
  await Promise.resolve(); await Promise.resolve();
  current = false; t.mock.timers.tick(100); await rejected;
  assert.equal(video.loop, true); assert.equal(video.autoplay, true);
  assert.equal(video.paused, true); assert.equal(video.playbackRate, 2);
});

test('lost audio track fails instead of uploading a silent remainder', async t => {
  t.mock.timers.enable({ apis: ['setTimeout', 'setInterval'] });
  const video = new Video(); const task = captureVideoElement(video);
  const rejected = assert.rejects(task, /audio track ended/);
  await Promise.resolve(); await Promise.resolve();
  video.tracks[0].readyState = 'ended'; t.mock.timers.tick(100); await rejected;
});

test('capture progress reflects the selected playback, not a fabricated percent', async t => {
  t.mock.timers.enable({ apis: ['setTimeout', 'setInterval'] });
  const video = new Video(); const readings = [];
  const task = captureVideoElement(video, { onProgress: reading => readings.push(reading) });
  await Promise.resolve(); await Promise.resolve();
  video.currentTime = 1; t.mock.timers.tick(100);
  assert.deepEqual(readings[0], { capturedSeconds: 1, durationSeconds: 2 });
  video.currentTime = 2; video.ended = true; video.dispatchEvent(new Event('ended'));
  await task;
});
