import test from 'node:test';
import assert from 'node:assert/strict';
import { captionForScreening, matchesSubmittedPost, isValidScreeningResult, matchesVideoPreview, postResultCacheKey, requireScreeningResult, resolveMediaChoice } from '../src/result_binding.js';

const submitted = { text: 'News caption about a city event.', pageUrl: 'https://www.facebook.com/search/top?q=news', pageTitle: 'News - Facebook' };
const response = { page_url: submitted.pageUrl, page_title: submitted.pageTitle, internal_label: 'Non-Misleading', public_label: 'No Misleading Information Detected', model_score: .2 };

test('missing, contradictory, or invalid predictions cannot become a clear label', () => {
  const valid = { ...response, analyzed_text: submitted.text };
  assert.equal(isValidScreeningResult(valid), true);
  for (const invalid of [{}, { ...valid, internal_label: null }, { ...valid, public_label: 'Potentially Misleading' },
    { ...valid, final_label: 'Potentially Misleading' }, ...[null, '0.2', NaN, Infinity, -1, 1.1].map(model_score => ({ ...valid, model_score }))]) {
    assert.equal(isValidScreeningResult(invalid), false);
    assert.throws(() => requireScreeningResult(invalid), /No prediction was displayed/);
    assert.equal(matchesSubmittedPost(invalid, { ...submitted, mediaChoice: 'text' }), false);
  }
});

test('evidence-only results do not require or accept a model score', () => {
  const result = {
    ...response,
    screening_mode: 'evidence_only',
    model_score: null,
    analyzed_text: submitted.text,
  };
  assert.equal(isValidScreeningResult(result), true);
  assert.equal(isValidScreeningResult({ ...result, model_score: .7 }), false);
  assert.equal(isValidScreeningResult({ ...result, model_score: '0.7' }), false);
  assert.throws(() => requireScreeningResult({ ...result, model_score: .7 }), /No prediction was displayed/);
});

test('caption-only results still require the exact submitted text', () => {
  assert.equal(matchesSubmittedPost({ ...response, input_type: 'text', analyzed_text: submitted.text }, { ...submitted, mediaChoice: 'text' }), true);
  assert.equal(matchesSubmittedPost({ ...response, input_type: 'text', analyzed_text: 'A neighboring post.' }, { ...submitted, mediaChoice: 'text' }), false);
});

test('cached result identity follows the post and selected media, not expiring media query strings', () => {
  const image = {
    ...submitted,
    context: { author: 'Abante Tonite', original_post_url: 'https://www.facebook.com/story.php?story_fbid=123' },
    media: { image_urls: ['https://fbcdn.net/photo/one.jpg?token=old'] },
  };
  const sameImage = { ...image, media: { image_urls: ['https://fbcdn.net/photo/one.jpg?token=new'] } };
  const differentImage = { ...image, media: { image_urls: ['https://fbcdn.net/photo/two.jpg?token=new'] } };
  assert.equal(postResultCacheKey(image, 'image'), postResultCacheKey(sameImage, 'image'));
  assert.notEqual(postResultCacheKey(image, 'image'), postResultCacheKey(differentImage, 'image'));
  assert.notEqual(postResultCacheKey(image, 'image'), postResultCacheKey({ ...image, text: 'A different post.' }, 'image'));
  assert.notEqual(postResultCacheKey(image, 'image'), postResultCacheKey(image, 'text'));
});

test('image results bind the caption and OCR text together', () => {
  const image = { ...response, input_type: 'image', analyzed_text: `${submitted.text} Memorial image text`, extraction: { caption_text: submitted.text, ocr_text: 'Memorial image text' } };
  assert.equal(matchesSubmittedPost(image, { ...submitted, mediaChoice: 'image' }), true);
  assert.equal(matchesSubmittedPost({ ...image, extraction: { ...image.extraction, caption_text: 'Another post' } }, { ...submitted, mediaChoice: 'image' }), false);
  assert.equal(matchesSubmittedPost({ ...image, analyzed_text: submitted.text }, { ...submitted, mediaChoice: 'image' }), false);
  assert.equal(matchesSubmittedPost({ ...image, page_url: 'https://www.facebook.com/other' }, { ...submitted, mediaChoice: 'image' }), false);
});

test('captionless images require readable OCR and matching analyzed text', () => {
  const input = { ...submitted, text: '', mediaChoice: 'image' };
  assert.equal(matchesSubmittedPost({ ...response, input_type: 'image', analyzed_text: 'Visible image claim', extraction: { caption_text: '', ocr_text: 'Visible image claim' } }, input), true);
  assert.equal(matchesSubmittedPost({ ...response, input_type: 'text', analyzed_text: 'Visible image claim', extraction: { caption_text: '', ocr_text: '' } }, input), false);
  assert.equal(matchesSubmittedPost({ ...response, input_type: 'image', analyzed_text: 'Caption only', extraction: { caption_text: '', ocr_text: 'Visible image claim' } }, input), false);
});

test('video results require the submitted caption and extracted media text', () => {
  const video = { ...response, input_type: 'video', analyzed_text: `${submitted.text} Spoken report`, extraction: { caption_text: submitted.text, transcript_text: 'Spoken report', frame_ocr_text: '' } };
  assert.equal(matchesSubmittedPost(video, { ...submitted, mediaChoice: 'video' }), true);
  assert.equal(matchesSubmittedPost({ ...video, analyzed_text: `${submitted.text}ual unrelated text` }, { ...submitted, mediaChoice: 'video' }), false);
  assert.equal(matchesSubmittedPost({ ...video, extraction: { caption_text: submitted.text, transcript_text: '', frame_ocr_text: '' } }, { ...submitted, mediaChoice: 'video' }), false);
});

test('video-only results require the exact extracted speech and frame text', () => {
  const input = { ...submitted, text: '', mediaChoice: 'video' };
  const video = { ...response, input_type: 'video', analyzed_text: 'Spoken report On-screen claim', extraction: { caption_text: '', transcript_text: 'Spoken report', frame_ocr_text: 'On-screen claim' } };
  assert.equal(matchesSubmittedPost(video, input), true);
  assert.equal(matchesSubmittedPost({ ...video, analyzed_text: submitted.text }, input), false);
  assert.equal(matchesSubmittedPost({ ...video, extraction: { ...video.extraction, caption_text: submitted.text } }, input), false);
});

test('unrelated frame text remains visible but is excluded from the screened speech', () => {
  const input = { ...submitted, text: '', mediaChoice: 'video' };
  const video = { ...response, input_type: 'video', analyzed_text: 'Spoken report', extraction: {
    caption_text: '', transcript_text: 'Spoken report', frame_ocr_text: 'Another story on screen',
    frame_ocr_included: false,
  } };
  assert.equal(matchesSubmittedPost(video, input), true);
  assert.equal(matchesSubmittedPost({ ...video, analyzed_text: 'Spoken report Another story on screen' }, input), false);
});

test('media posts always show the chooser again and explicit video never degrades to text', () => {
  assert.equal(resolveMediaChoice('auto', { has_video: true }), 'choose');
  assert.equal(resolveMediaChoice('auto', { has_video: true, image_urls: [] }), 'choose');
  assert.equal(resolveMediaChoice('video', { has_video: false }), 'unavailable');
  assert.equal(resolveMediaChoice('video', { has_video: true }), 'video');
  assert.equal(resolveMediaChoice('image', { image_urls: [] }), 'unavailable');
  assert.equal(resolveMediaChoice('text', { has_video: true }), 'text');
});

test('collapsed captions are excluded from image and video checks instead of blocking media extraction', () => {
  assert.equal(captionForScreening('Collapsed caption…', false, 'video'), '');
  assert.equal(captionForScreening('Collapsed caption…', false, 'image'), '');
  assert.equal(captionForScreening('Collapsed caption…', false, 'text'), 'Collapsed caption…');
  assert.equal(captionForScreening('Complete caption', true, 'video'), 'Complete caption');
});

test('video extraction preview binds the caption and requires extracted media text', () => {
  const preview = {
    review_required: true,
    review_token: 'one-time-review',
    page_url: submitted.pageUrl,
    page_title: submitted.pageTitle,
    post_text: submitted.text,
    extraction: { transcript_text: 'Words spoken in the video', frame_ocr_text: '', frame_ocr_included: true },
  };
  const binding = { text: submitted.text, pageUrl: submitted.pageUrl, pageTitle: submitted.pageTitle };
  assert.equal(matchesVideoPreview(preview, binding), true);
  assert.equal(matchesVideoPreview({ ...preview, post_text: '' }, binding), false);
  assert.equal(matchesVideoPreview({ ...preview, extraction: { transcript_text: '', frame_ocr_text: '' } }, binding), false);
});
