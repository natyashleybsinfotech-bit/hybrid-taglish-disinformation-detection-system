# Evidence decision trial and readiness — 14 November 2026

The user requested a model-plus-evidence trial, followed by checks across the
extension, API, dashboard, database and deployment preparation. This report does
not declare every prediction or transcript correct.

## Current local behavior

The original hybrid remains active: `model_4.joblib`, run `20261011T235112Z`,
threshold `0.65`, SHA-256
`72d87971ee2af7fca1f6f0a9b94bbe92618bd92ce8c5e48e35b80882e1321c7c`.
No classifier was trained or tuned. Extension build: **1.3.39**.

The final label can follow readable claim-specific evidence when:

- A narrowly scoped primary authority directly supports or explicitly contradicts
  the claim in its subject area; or
- Two distinct trusted publishers with non-duplicate article bodies do so.

The current primary-authority scopes are CDC/WHO/DOH public-health topics and
Bureau of Customs reports about Customs. Being a government website by itself
does not qualify. The source must still pass the same body-assertion checks.

Headline overlap, search previews, inaccessible pages and partial support of a
multi-statement post cannot change the label. Conflicting trusted evidence blocks
an override. Relative event dates such as “next week” remain ineligible until their
time is aligned with the post. Written quantities such as three/four are checked.
Unverified or insufficient evidence leaves the original model prediction in place,
with an explicit unverified explanation. No link is not a falsehood verdict.

Matching passages and the source links are available in expandable English/Tagalog
source cards. The original model label and score remain separate; the final
evidence decision has no invented numerical confidence. Later source-only lookup
still does not recalculate an existing final label; enable source retrieval for the
initial analysis, or use Check again with retrieval enabled.

## Checks completed

- **214 backend tests passed**, including API passage export, original-score
  preservation, direct support/debunk, conflicting assertions, partial claims,
  wrong quantities, hypothetical text and out-of-scope primary sources.
- **34 extension behavior tests passed**, product contract passed, extension built.
- Admin dashboard lint and production build passed.
- Actual local dashboard/API login, session reload, logout, viewer access, expired
  session rejection and narrow layout passed in isolated Google Chrome.
- Extension 1.3.39 passed the installed-unpacked-extension/local Facebook fixture
  rehearsal in isolated Microsoft Edge. This included image-choice detection,
  selecting only the target video, excluding comments/neighbouring posts, bilingual
  result order and stale-result handling. No logged-in real Facebook account was
  used in that rehearsal.
- Twelve rendered views cover popup, media, matching passage and admin layouts,
  including narrow Tagalog. The passage-layout examples are explicitly controlled
  fixtures; their screenshots are not factual classification evidence.
- MariaDB schema 6: isolated provisioning/migrations, runtime DDL rejection,
  rollback, persistence across restart, outage handling and backup/restore passed.
- Controlled image OCR found the expected phrase. Controlled video extraction
  found the expected speech/OCR words. These are synthetic English smoke checks,
  not measured natural Filipino/Taglish transcription accuracy.
- Deployment static configuration/artifact checks passed. Docker is not installed;
  no Linux/container stack, public HTTPS or remote capacity test was performed.

Some initial browser harness runs could not connect to their isolated debugging
targets; the isolated reruns succeeded without changing Windows security settings.

## Live source examples

`tmp/evidence-trial-live-20261114.json` records actual local API requests and
configured provider retrieval, not mocked article bodies:

- Hydration statement: raw model warned; a readable CDC body passage supported
  the statement within its public-health scope; final label became
  **No Misleading Information Detected**.
- BOC vape-destruction statement: raw model warned; readable matching Philstar
  and Daily Tribune body passages supported the claim; final label became
  **No Misleading Information Detected**. An inaccessible result was not used.

These two examples verify those flows, not general accuracy. The evidence gate is
a bounded lexical/anchor heuristic, not complete semantic entailment. It may miss
paraphrases, complex numbers, attribution, implied contradictions or time context.
The classifier's known errors remain when evidence is unavailable or inconclusive.
The generic PAGASA provider probe returned no results; that was recorded as such,
not as a successful claim verification. Google fact-check search returned a result,
but search matches alone do not determine the final label.

## Handoff and remaining checks

1. In the user's Chrome, reload SuriPH on `chrome://extensions`, confirm **1.3.39**,
   then refresh Facebook. Enable source retrieval on the initial check.
2. Complete a logged-in Facebook rehearsal with the intended text, image and
   natural-news-video tasks. Prior material errors in the GMA transcript have not
   been resolved by this evidence-decision change. Confirm the extracted text
   against the original material before accepting the video flow for a survey.
3. Before public deployment, run the release on the chosen server and verify
   HTTPS, restart/recovery, external extension connectivity and expected load.

**Status:** the local evidence trial is implemented and checked. Full survey and
public-deployment readiness are **not yet established** by this run. No public
deployment, new accuracy estimate or Git push was performed.

Evidence records: `tmp/backend-evidence-trial-20261114.log`,
`tmp/extension-evidence-trial-20261114.log`, `docs/ADMIN-BROWSER-VERIFICATION.json`,
`docs/FACEBOOK-MODAL-VERIFICATION.json`, `docs/UI-VERIFICATION.json`,
`docs/MARIADB-VERIFICATION.json` (if generated by the local verifier),
`docs/MEDIA-VERIFICATION.json`, and `docs/DEPLOYMENT-VERIFICATION.json`.
