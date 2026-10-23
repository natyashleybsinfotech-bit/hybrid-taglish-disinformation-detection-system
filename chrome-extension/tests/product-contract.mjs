import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const manifest = JSON.parse(await readFile(new URL('../manifest.json', import.meta.url), 'utf8'));
const popup = await readFile(new URL('../src/Popup.jsx', import.meta.url), 'utf8');
const content = await readFile(new URL('../src/content.js', import.meta.url), 'utf8');
const background = await readFile(new URL('../src/background.js', import.meta.url), 'utf8');
const api = await readFile(new URL('../src/api.js', import.meta.url), 'utf8');

assert.equal(manifest.version, '1.4.0');
assert.deepEqual(manifest.content_scripts[0].matches, ['*://*.facebook.com/*']);
for (const forbidden of ['*://*.x.com/*', '*://*.twitter.com/*', '*://*.youtube.com/*', '*://*.reddit.com/*'])
  assert.ok(!manifest.host_permissions.includes(forbidden), `Unexpected permission: ${forbidden}`);
assert.match(content, /Fail closed[\s\S]{0,240}return '';/);
assert.match(content, /function readableCaptionText\(node\)/);
assert.match(content, /current\.matches\?\.\(CAPTION_CONTROL_SELECTOR\)/);
assert.match(content, /boundaryDisplays/);
assert.doesNotMatch(content, /replace\([^\n]{0,100}(?:See|see)\s+(?:more|less)/);

for (const source of [popup, content]) {
  assert.match(source, /assessment_label/);
  assert.match(source, /assessment_basis/);
  assert.match(source, /fact_check_matches/);
  assert.match(source, /related_sources/);
  assert.match(source, /No trained classifier|Walang trained classifier/);
  for (const forbidden of ['Potentially Misleading', 'No Misleading Information Detected', 'P(Misleading)', 'model_score', 'decision_threshold', 'linguistic_indicators'])
    assert.ok(!source.includes(forbidden), `Active UI still contains classifier output: ${forbidden}`);
}
assert.match(content, /SURIPH_LOOKUP_SOURCES/);
assert.match(background, /SURIPH_LOOKUP_SOURCES/);
assert.match(background, /\/related-sources/);
assert.match(api, /lookupRelatedSources/);
assert.doesNotMatch(api, /submitCandidate|\/candidates/);

const expectedParts = ['1-assessment', '2-basis', '3-post-context', '4-fact-checks', '5-related-sources', '6-analyzed-text', '7-reminder', '8-check-again'];
assert.deepEqual([...popup.matchAll(/data-result-part="([^"]+)"/g)].map(match => match[1]), expectedParts);
for (const part of expectedParts) assert.match(content, new RegExp(part), `Facebook result is missing ${part}`);

const englishReminder = 'SuriPH searches for published fact-checks and related reporting. Related links are context, not proof. If no closely matching published fact-check is available, SuriPH leaves the post unresolved.';
const tagalogReminder = 'Naghahanap ang SuriPH ng published fact-checks at kaugnay na ulat. Konteksto lamang ang related links, hindi patunay. Kung walang malapit na published fact-check, mananatiling unresolved ang post.';
assert.equal(popup.split(englishReminder).length - 1, 1);
assert.equal(popup.split(tagalogReminder).length - 1, 1);
assert.equal(content.split(englishReminder).length - 1, 1);
assert.equal(content.split(tagalogReminder).length - 1, 1);
assert.match(content, /author[\s\S]{0,1000}published_at[\s\S]{0,1000}original_post_url[\s\S]{0,1000}visible_links/);
assert.match(content, /context\.relevant_links/);
assert.doesNotMatch(popup, /participant|questionnaire|survey|candidate/i);

console.log(JSON.stringify({
  facebook_only_manifest: 'passed', bounded_extraction: 'passed', evidence_only_ui: 'passed',
  no_classifier_output: 'passed', exact_eight_part_order: 'passed', fact_check_panel: 'passed',
  related_sources_are_context: 'passed', candidate_ui_absent: 'passed', survey_ui_absent: 'passed',
}));
