import test from 'node:test';
import assert from 'node:assert/strict';
import { statusTone } from '../src/status.js';

test('unavailable or unverified services cannot appear green', () => {
  for (const state of ['unavailable', 'unavailable_not_configured', 'inaccessible', 'offline', 'not_available', 'not_connected']) assert.equal(statusTone(state), 'red');
  for (const state of ['unverified', 'not_verified', 'not_configured', 'not_ready', 'not_assessed', null]) assert.equal(statusTone(state), 'amber');
  for (const state of ['available', 'configured', 'ready', 'verified', 'healthy']) assert.equal(statusTone(state), 'green');
});
