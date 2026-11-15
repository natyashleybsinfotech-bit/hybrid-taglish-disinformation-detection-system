# SuriPH defense readiness — 15 November 2026

This is a check of the current local build, not a new accuracy evaluation. The
active classifier remains the original hybrid `model_4.joblib`, run
`20261011T235112Z`, SHA-256
`72d87971ee2af7fca1f6f0a9b94bbe92618bd92ce8c5e48e35b80882e1321c7c`,
threshold `0.65`. The two public labels remain **No Misleading Information
Detected** and **Potentially Misleading**. No retraining, model switch, manual
post exception or threshold change was made.

## False-positive investigation and fix

- A locally submitted supported short claim still produced a raw model warning.
  This is a classifier error, not a display-only defect. Recent stored decisions
  retain hashes rather than submitted post text, so the user's latest Facebook
  cases cannot be attributed from the database alone.
- A news claim about the National AI Council exposed an evidence failure:
  `created/creating/creation` and `adopted/adoption` did not match the claim's
  `creates/adopts` actions. Some publisher bodies joined sentences without a
  space, so a direct passage was hidden in an oversized text window. Common
  suffixes such as `Jr.` also split one claim into two pieces.
- The evidence gate now recognizes those action forms, preserves common name
  abbreviations, recovers joined sentence boundaries, requires the named actor,
  and rejects future plans, wrong actors and negated actions as proof of a
  completed event. It selects the shortest directly matching body passage.
  The article reader removes a Rappler sign-in/AI-summary prompt that leaked
  into an excerpt. Search snippets, headline similarity, unreadable URLs and
  merely related articles still cannot override the model.
- **Actual running API replay, no supplied source links:** `President Ferdinand
  Marcos Jr. created the National AI Council and adopted an AI governance
  framework.` Raw model: **Potentially Misleading**, score
  `0.999999991424254`. With source retrieval off, the final label remains that
  model warning. With retrieval on, readable matching passages from
  [Philstar](https://www.philstar.com/headlines/2026/11/15/2570133/marcos-creates-national-ai-council-adopts-governance-framework)
  and [Rappler](https://www.rappler.com/technology/marcos-jr-creates-national-artificial-intelligence-council-governance-framework/)
  changed the final label to **No Misleading Information Detected** under the
  two-independent-publisher rule. The first live call took 4.59 s; the
  final post-cleanup replay took 4.20 s on this workstation. Times are observations,
  not an SLA. An earlier call before those two articles were retrieved retained
  the model warning with only one readable supporter; that conservative fallback
  remains correct when evidence is insufficient.
- Before cleanup, the Rappler matching passage contained `Read the article for
  full context. Report any errors.` and, on the next replay, an unrelated
  photo-caption sentence. The reader prompt is now excluded and the matching
  excerpt selects the shortest asserting sentence. A separate real-page read
  confirmed the prompt is absent from the cleaned article text. The final live
  API replay showed neither the prompt nor the unrelated `TURNOVER` caption in
  the two evidence passages.

This is one verified live API example. It does not establish a lower population
false-positive rate. A seven-case diagnostic of a different, full-cleaned
candidate showed fewer warnings on several supported claims but incorrectly
accepted three CDC/WHO-debunked COVID claims. Those cases were not an
independently reviewed evaluation. Switching to that candidate would trade one
error type for another, so it was not activated.

## General action and source-discovery follow-up

The user correctly challenged a one-post-only repair. A cross-topic controlled
probe showed the same defect for four ordinary headline/report pairs:
`opens/opened`, `approves/approved`, `files/filed`, and
`recommends/recommended`. Before this repair, two directly supporting readable
publisher bodies were marked merely related in **all four** pairs, leaving the
raw warning. The shared search/evidence term normalization now treats those
inflected actions consistently; after repair, all four pairs are assessed as
supporting and satisfy the existing two-publisher rule. Future plans, negated
actions and changed quantities remain blocked in regression tests. This is a
software probe, not a real-world accuracy estimate.

The search ranking no longer discards a direct international source merely
because a Philippine result exists. Local publishers still win equal-relevance
ties. A test covers a directly relevant CDC health result alongside a local
question headline. No source is deemed true because of its domain or search
preview; the readable body and claim-specific gate are still required.

An advocacy claim exposed a separate, reusable semantic gap: `calls for` in a
headline and `calling for` in a body were not recognized as the same action;
`pay/salaries` and `teachers/teacher` also broke alignment. Those terms now
normalize only in the evidence assessor. Advocacy remains distinct from an
enacted pay raise, and a negative `not calling for` cannot become support.

Six further live API checks used provider discovery with **no manually supplied
links** (`tmp/general-fp-replay-20261115.json` before the advocacy edit and
`tmp/general-fp-after-20261115.json` after the action/search edits):

| Claim type | Raw model | Final after | Source observation |
| --- | --- | --- | --- |
| Hydration | Potentially Misleading | No Misleading Information Detected | Direct readable CDC support within its health scope. |
| BOC vape destruction | Potentially Misleading | No Misleading Information Detected | Two readable independent supporting publishers. |
| National AI Council | Potentially Misleading | No Misleading Information Detected | Two readable independent supporting publishers. |
| ACT Teachers advocacy | Potentially Misleading | Potentially Misleading | One readable GMA article now correctly assessed as supporting; the evidence rule still falls back to the model because no second independent readable report was found. |
| Vaccine microchip myth | Potentially Misleading | Potentially Misleading | No readable supporting evidence; no evidence override. |
| Water-every-15-minutes COVID myth | Potentially Misleading | Potentially Misleading | Two readable articles were merely related under the current strict gate; no evidence override. |

These six selected checks demonstrate behavior across topics, not a measured
false-positive or false-negative rate. In particular, the ACT Teachers result
is still a visible false-positive risk. The original classifier assigns very
high misleading scores to several supported short statements. When the
required readable evidence is missing, the two-label policy retains that
model output with an explicit unverified explanation. Fixing that underlying
generalization requires a separately reviewed labeled evaluation and model
repair; inventing a new threshold or treating related links as proof would
hide the problem.

## Build and test record

- Backend: **226 passed** in the isolated Python environment; full result in
  `tmp/backend-general-fp-20261115.log`. This includes mismatched actors, plans,
  negation, article prompt removal, photo-caption exclusion, no-source fallback
  and the original two-label contract.
- Extension: production build passed, **34 tests** passed, product contract
  passed. Logs: `tmp/extension-build-20261115.log`,
  `tmp/extension-tests-20261115.log`, `tmp/extension-contract-20261115.log`.
- Admin dashboard: lint, production build and **1 test** passed. Logs in
  `tmp/admin-*-20261115.log`.
- Isolated local Facebook fixture: extension modal, selected-post binding,
  switching posts during analysis, incomplete caption, author/date scope,
  source-only lookup, bilingual labels and result order passed. The fixture
  explicitly reports `actual_facebook_account_tested: false`; see
  `tmp/facebook-modal-20261115.log` and `docs/FACEBOOK-MODAL-VERIFICATION.json`.
- Isolated admin browser: login, session reload, logout, expired-session 401,
  viewer separation and narrow layout passed; see
  `tmp/admin-browser-20261115.log` and `docs/ADMIN-BROWSER-VERIFICATION.json`.
- The restarted local `/ready` returned `ready: true`, MariaDB `available`,
  and the pinned original model `ready` at threshold `0.65`.
- Earlier Windows Application Control blocked SQLAlchemy
  `_util_cy.cp313-win_amd64.pyd` for an affected backend run. The complete
  backend suite above ran in an approved isolated Python environment without
  changing Windows security controls. The Windows-specific block remains a
  workstation risk separate from the test result.

## Readiness decisions

| Track | Current decision | Required observation |
| --- | --- | --- |
| Defense demo | **Conditional local rehearsal.** Text evidence behavior and build gates passed. | Reload extension 1.3.39 in the user's Chrome, refresh Facebook, then replay the actual posts with captured analyzed text, source cards, and post date. Avoid claiming a validated natural-video transcript. |
| Participant survey | **Not ready to release.** | Questionnaire item 1.4 remains **Failed**: the original GMA reel has material speech errors and no complete listening-checked reference. Signed-in Facebook observations and adviser/institutional review are pending. |
| Public deployment | **Not ready.** | No tested target host, HTTPS origin, Linux/container run, recovery drill on the target or external-client capacity result. Local MariaDB/API availability is not a deployment test. |

The existing 45-item questionnaire checklist is
[`research/QUESTIONNAIRE-ACCEPTANCE-20261110.md`](research/QUESTIONNAIRE-ACCEPTANCE-20261110.md).
No unobserved participant item was changed to Passed. Actual Facebook post URLs,
the visible analyzed text/result and sources are still needed to reproduce the
user's latest wrong predictions on the same build. Keep original GMA item 1.4
Failed until a listening-checked retest passes.
