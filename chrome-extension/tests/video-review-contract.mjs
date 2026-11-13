import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const background = readFileSync(new URL('../src/background.js', import.meta.url), 'utf8');
const content = readFileSync(new URL('../src/content.js', import.meta.url), 'utf8');
const popupApi = readFileSync(new URL('../src/api.js', import.meta.url), 'utf8');
const binding = readFileSync(new URL('../src/result_binding.js', import.meta.url), 'utf8');

test('Facebook video analysis reviews mismatched speech/frame text before classification', () => {
  assert.ok(background.includes("postMediaBlob('extract/video'"));
  assert.ok(background.includes("postMedia('extract/video'"));
  assert.ok(background.includes("postMediaBlob('analyze/video'"));
  assert.ok(background.includes("port.name !== 'SURIPH_VIDEO_ANALYSIS'"));
  assert.ok(background.includes("port.onMessage.addListener(message =>"));
  assert.ok(background.includes("port.postMessage({ ok: true, result })"));
  assert.ok(background.includes("message?.type === 'SURIPH_CONFIRM_VIDEO'"));
  assert.ok(popupApi.includes("kind === 'video' ? '/extract/video'"));
  assert.ok(popupApi.includes("request('/analyze/confirmed-video'"));
  assert.ok(content.includes('analyzeCapturedVideo(videoBase64'));
  assert.ok(content.includes("chrome.runtime.connect({ name: 'SURIPH_VIDEO_ANALYSIS' })"));
  assert.ok(content.includes("port.postMessage({ type: 'PING' })"));
  assert.ok(content.includes('response?.result?.review_required'));
  assert.ok(content.includes('renderVideoReview({'));
  assert.ok(content.includes('renderRichResult(result, response.result)'));
  assert.ok(content.includes('matchesVideoPreview(preview'));
  assert.ok(content.includes('collectPostText(post) !== snapshot.text'));
  assert.ok(content.includes('transcript_text: extraction.transcript_text, frame_ocr_text: extraction.frame_ocr_text'));
  assert.ok(content.includes("text: snapshot.submittedText, mediaChoice: 'video'"));
  assert.ok(content.includes("mediaChoice: 'video', pageUrl: snapshot.pageUrl"));
  assert.ok(binding.includes('normalize(preview.post_text) !== normalize(text)'));
  assert.ok(binding.includes('resolveMediaChoice(choice, media)'));
  assert.ok(binding.includes('captionForScreening(text, isComplete, mode)'));
  assert.ok(content.includes("extraction.speech_frame_agreement === 'review_required'"));
  assert.ok(content.includes('Compare both with the video before confirming.'));
});
