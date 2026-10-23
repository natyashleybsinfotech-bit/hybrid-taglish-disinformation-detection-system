import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const manifest = JSON.parse(await readFile(new URL('../manifest.json', import.meta.url), 'utf8'));
const popup = await readFile(new URL('../src/Popup.jsx', import.meta.url), 'utf8');
const content = await readFile(new URL('../src/content.js', import.meta.url), 'utf8');
const background = await readFile(new URL('../src/background.js', import.meta.url), 'utf8');
const api = await readFile(new URL('../src/api.js', import.meta.url), 'utf8');

assert.deepEqual(manifest.content_scripts[0].matches, ['*://*.facebook.com/*']);
for (const forbidden of ['*://*.x.com/*', '*://*.twitter.com/*', '*://*.youtube.com/*', '*://*.reddit.com/*', '*://*.twimg.com/*', '*://*.googlevideo.com/*', '*://*.redd.it/*'])
  assert.ok(!manifest.host_permissions.includes(forbidden), `Unexpected permission: ${forbidden}`);
for (const forbidden of ['tweetText', 'ytd-watch', 'reddit']) assert.ok(!content.includes(forbidden), `Unexpected content selector/support: ${forbidden}`);
for (const forbidden of ['x.com', 'twimg.com', 'youtube.com', 'googlevideo.com', 'reddit.com', 'redd.it']) assert.ok(!background.includes(`'${forbidden}'`), `Unexpected media origin: ${forbidden}`);
assert.match(content, /Fail closed[\s\S]{0,240}return '';/, 'Facebook extraction must fail closed without a recognized message node');
assert.match(content, /function readableCaptionText\(node\)/, 'Recognized captions must preserve visible text boundaries');
assert.match(content, /current\.matches\?\.\(CAPTION_CONTROL_SELECTOR\)/, 'Actual DOM controls inside a caption must be skipped');
assert.match(content, /boundaryDisplays/, 'Block boundaries inside Facebook captions must remain separated');
assert.doesNotMatch(content, /replace\([^\n]{0,100}(?:See|see)\s+(?:more|less)/, 'User-authored See more/See less text must not be deleted by phrase matching');
assert.match(content, /appendLookupChoice/, 'The in-page Facebook flow must expose source lookup before analysis');
assert.match(content, /context_explanation/, 'The in-page result must render the backend context');
assert.match(content, /SURIPH_LOOKUP_SOURCES/, 'The in-page result must support a source-only lookup');
assert.match(background, /SURIPH_LOOKUP_SOURCES/);
assert.match(background, /\/related-sources/);
assert.match(background, /suriphSourceDefaultVersion/);
assert.match(background, /suriphRetrieveSources:\s*true/, 'The 1.3.1 update must enable public source lookup once');
assert.match(api, /lookupRelatedSources/);
assert.match(api, /\/related-sources/);
assert.match(popup, /Potentially Misleading/);
assert.match(popup, /No Misleading Information Detected/);
assert.match(popup, /This is the model score for the displayed class\./);
assert.match(popup, /Ito ang model score para sa ipinapakitang class\./);
assert.match(popup, /suriphLanguage/);
assert.match(popup, /consentToStore: true/);
assert.match(popup, /candidateState === 'submitted'/);
assert.match(popup, /candidateLock\.current/, 'Candidate submission must use a synchronous duplicate-request guard');
assert.match(popup, /context_explanation/, 'The popup result must render the backend context');
assert.doesNotMatch(popup, /Published fact-check reviews|fact_check_matches/, 'Google Fact Check is not a public result section');
assert.doesNotMatch(content, /Published fact-check reviews|fact_check_matches/, 'Google Fact Check is not a public result section');
const popupParts = [...popup.matchAll(/data-result-part="([^"]+)"/g)].map(match => match[1]);
assert.deepEqual(popupParts, [
  '1-prediction', '2-score', '3-post-context', '4-features',
  '5-related-sources', '6-analyzed-text', '7-reminder', '8-check-again',
]);
for (const part of ['1-prediction', '2-score', '3-post-context', '4-features', '5-related-sources', '6-analyzed-text', '7-reminder', '8-check-again'])
  assert.match(content, new RegExp(part), `Facebook result is missing ${part}`);
const englishReminder = 'SuriPH is an automated screening tool that may produce incorrect predictions. Its label and score do not confirm whether a claim is true or false. Review the original post’s date, source and full context, and consult credible references before sharing or acting on the information.';
const tagalogReminder = 'Ang SuriPH ay awtomatikong kasangkapan sa paunang pagsusuri na maaaring magkamali. Hindi pinatutunayan ng label at score nito kung totoo o mali ang isang pahayag. Suriin ang petsa, pinagmulan at buong konteksto ng post, at kumonsulta sa mapagkakatiwalaang sanggunian bago ibahagi o aksyunan ang impormasyon.';
assert.equal(popup.split(englishReminder).length - 1, 1, 'Popup must contain exactly one English reminder');
assert.equal(popup.split(tagalogReminder).length - 1, 1, 'Popup must contain exactly one Tagalog reminder');
assert.equal(content.split(englishReminder).length - 1, 1, 'Facebook modal must contain exactly one English reminder');
assert.equal(content.split(tagalogReminder).length - 1, 1, 'Facebook modal must contain exactly one Tagalog reminder');
assert.match(content, /author[\s\S]{0,1000}published_at[\s\S]{0,1000}original_post_url[\s\S]{0,1000}visible_links/, 'Facebook extraction must collect bounded post metadata');
assert.match(content, /context\.relevant_links/, 'Facebook result must render backend-filtered post links');
assert.doesNotMatch(popup, /participant|questionnaire|survey/i);

console.log(JSON.stringify({
  facebook_only_manifest: 'passed', bounded_extraction: 'passed', bilingual_fixed_copy: 'passed',
  cautious_labels: 'passed', exact_eight_part_order: 'passed', one_bottom_reminder: 'passed',
  in_page_lookup_control: 'passed', source_lookup_update_default: 'passed', source_only_lookup_path: 'passed', public_fact_check_panel_absent: 'passed',
  context_visible: 'passed', bounded_post_metadata: 'passed', explicit_candidate_consent: 'passed', duplicate_candidate_guard: 'passed', survey_ui_absent: 'passed',
}));
