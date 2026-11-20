import test from 'node:test';
import assert from 'node:assert/strict';
import { evidenceReaderNotice } from '../src/result_updates.js';
test('evidence-service failures do not masquerade as an assessed unsupported claim', () => {
  for (const status of ['rate_limited','busy','unavailable','authentication_failed','invalid_response','incomplete_response','source_limit_exceeded']) {
    assert.match(evidenceReaderNotice({evidence_reader:{status}}), /unverified model prediction/);
    assert.match(evidenceReaderNotice({evidence_reader:{status}},'tl'), /hindi pa beripikadong model prediction/i);
  }
});
test('no readable body is distinct from an assessed related article', () => {
  assert.match(evidenceReaderNotice({evidence_reader:{status:'no_readable_sources'}}), /No readable article/);
  assert.equal(evidenceReaderNotice({evidence_reader:{status:'assessed'}}),'');
});
test('verified evidence does not show an unrelated reader-failure warning', () => {
  assert.equal(evidenceReaderNotice({decision_source:'verified_evidence',evidence_reader:{status:'busy'}}),'');
});
