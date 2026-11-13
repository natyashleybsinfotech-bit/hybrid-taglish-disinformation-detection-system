import test from 'node:test';
import assert from 'node:assert/strict';
import { mergeRelatedSources, checkedMaterialLabel, incompleteVideoNotice } from '../src/result_updates.js';

test('late source response cannot resurrect a cleared result or alter another post', () => {
  const first = { analyzed_text: 'First claim', internal_label: 'Misleading', model_score: .8 };
  const second = { analyzed_text: 'Second claim', internal_label: 'Non-Misleading', model_score: .1 };
  const sources = { retrieval_status: 'available', related_sources: [{ url: 'https://example.org/first' }] };
  assert.equal(mergeRelatedSources(null, first, sources), null);
  assert.equal(mergeRelatedSources(second, first, sources), second);
  const updated = mergeRelatedSources(first, first, sources);
  assert.equal(updated.internal_label, first.internal_label);
  assert.equal(updated.model_score, first.model_score);
  assert.deepEqual(updated.related_sources, sources.related_sources);
});

test('source-only refresh preserves the existing evidence decision', () => {
  const evidence = { url: 'https://example.org/assessed', relationship: 'supports' };
  const original = { evidence_relationship: 'supports', decision_source: 'verified_evidence', internal_label: 'Non-Misleading', related_sources: [evidence] };
  const updated = mergeRelatedSources(original, original, { retrieval_status: 'no_results', related_sources: [] });
  assert.equal(updated.evidence_relationship, 'supports');
  assert.equal(updated.decision_source, 'verified_evidence');
  assert.deepEqual(updated.related_sources, [evidence]);
});

test('media description reports only material actually extracted', () => {
  const context = 'Facebook post video audio transcript and video-frame OCR';
  assert.equal(checkedMaterialLabel(context, { transcript_text: 'Speech', frame_ocr_text: '' }, 'en'), 'Spoken audio');
  assert.equal(checkedMaterialLabel('Facebook post image OCR', { caption_text: '', ocr_text: 'Image words' }, 'en'), 'Text in the image');
  assert.equal(checkedMaterialLabel(context, { transcript_text: '', frame_ocr_text: 'Visible notice' }, 'tl'), 'Tekstong nasa mga video frame');
  assert.equal(checkedMaterialLabel(context, { caption_text: 'Caption', transcript_text: 'Speech', frame_ocr_text: 'Frame' }, 'en'), 'Post caption · Spoken audio · Text in video frames');
});

test('failed frame reader is distinct from no visible readable text', () => {
  assert.match(incompleteVideoNotice({ frame_ocr_status: 'failed' }, 'en'), /incomplete/);
  assert.match(incompleteVideoNotice({ frame_ocr_status: 'partial' }, 'tl'), /Kulang/);
  assert.equal(incompleteVideoNotice({ frame_ocr_status: 'no_readable_text' }, 'en'), '');
});
