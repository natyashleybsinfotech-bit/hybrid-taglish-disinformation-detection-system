import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const manifest = JSON.parse(await readFile(new URL('../manifest.json', import.meta.url), 'utf8'));
const popup = await readFile(new URL('../src/Popup.jsx', import.meta.url), 'utf8');
const content = await readFile(new URL('../src/content.js', import.meta.url), 'utf8');
const background = await readFile(new URL('../src/background.js', import.meta.url), 'utf8');

assert.deepEqual(manifest.content_scripts[0].matches, ['*://*.facebook.com/*']);
for (const forbidden of ['*://*.x.com/*', '*://*.twitter.com/*', '*://*.youtube.com/*', '*://*.reddit.com/*', '*://*.twimg.com/*', '*://*.googlevideo.com/*', '*://*.redd.it/*'])
  assert.ok(!manifest.host_permissions.includes(forbidden), `Unexpected permission: ${forbidden}`);
for (const forbidden of ['tweetText', 'ytd-watch', 'reddit']) assert.ok(!content.includes(forbidden), `Unexpected content selector/support: ${forbidden}`);
for (const forbidden of ['x.com', 'twimg.com', 'youtube.com', 'googlevideo.com', 'reddit.com', 'redd.it']) assert.ok(!background.includes(`'${forbidden}'`), `Unexpected media origin: ${forbidden}`);
assert.match(content, /Fail closed[\s\S]{0,240}return '';/, 'Facebook extraction must fail closed without a recognized message node');
assert.doesNotMatch(content, /cloneNode\(true\)/, 'Whole post/feed fallback must not be reachable');
assert.match(popup, /Potentially Misleading/);
assert.match(popup, /No Misleading Information Detected/);
assert.match(popup, /This score describes the model’s prediction\. It does not confirm whether the claim is true\./);
assert.match(popup, /Ang score na ito ay para sa hula ng modelo\. Hindi nito pinatutunayang totoo o mali ang pahayag\./);
assert.match(popup, /suriphLanguage/);
assert.match(popup, /consentToStore: true/);
assert.match(popup, /candidateState === 'submitted'/);
assert.match(popup, /candidateLock\.current/, 'Candidate submission must use a synchronous duplicate-request guard');
assert.doesNotMatch(popup, /participant|questionnaire|survey/i);

console.log(JSON.stringify({
  facebook_only_manifest: 'passed', bounded_extraction: 'passed', bilingual_fixed_copy: 'passed',
  cautious_labels: 'passed', explicit_candidate_consent: 'passed', duplicate_candidate_guard: 'passed', survey_ui_absent: 'passed',
}));
