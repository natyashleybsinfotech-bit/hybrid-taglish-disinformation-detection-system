# System refinement — 12 November 2026

## Applied locally

- Extension version **1.3.17** rejects missing labels, inconsistent public/final labels, empty analyzed text, and missing/non-numeric/out-of-range scores. A malformed success response cannot fall through to a Non-Misleading banner. The image result must also identify itself as image input and match its extracted OCR.
- The existing eight-part output order, two English prediction labels, English/Tagalog explanations, bottom reminder and explicit video transcript review remain in place.
- Retrieval scores all same-publisher candidates before choosing the strongest. An earlier weak result can no longer hide a later stronger match from that publisher.
- The article reader can use a publisher's explicit structured articleBody only when its HTTPS URL identifies the requested page. Descriptions, other-page metadata, conflicting bodies and HTML-filled metadata are not treated as article prose.
- Article redirects are limited to two hops within the same publisher, HTTPS only, with an overall eight-second request budget. Cross-publisher redirects, insecure redirects and loops fail closed. Existing fetched-body relevance and amount checks still apply.
- The explicit public-health source list now includes CDC and NHS alongside WHO. Lookalike hostnames remain excluded. Being on the list does not establish relevance or truth.
- Evidence matching rejects questions, hypotheticals and embedded quotations as factual assertions. A question beginning with “False:” is not a debunk. The www and non-www versions of the same host are not independent sources.
- Admin status badges resolve unavailable/unverified/not-configured states before positive status words. The status page has readable service names, last-check time, refresh/retry, separate speech-reader settings and a provider-configuration explanation. A failed refresh hides stale healthy service cards until recovery.
- The API was restarted with these changes. MariaDB and the pinned hybrid classifier remain active. No training, threshold change, alternative classifier, public deployment or publication was performed.

## Verification

| Check | Observed result |
| --- | --- |
| Backend | 136 tests passed; private log `tmp/backend-refinement-20261112.log` |
| Extension | Seven result-binding/video-review tests passed; product contracts and build passed |
| Admin | Status regression test, lint and build passed |
| Actual local admin/API in isolated Google Chrome | Login, cookie reload, logout, restricted viewer, desktop/narrow layout, refresh, blocked-status-request handling and recovery passed. Private report `tmp/ADMIN-REFINEMENT-20261112.json` |
| Rebuilt unpacked extension in isolated Edge | Controlled HTTPS Facebook fixture passed selected-post isolation, incomplete-caption rejection, stale-result handling, language stability, eight-part layout and source-only lookup. `actual_facebook_account_tested` is false |
| Live image acquisition | Server OCR read `READ THE COMPLETE REPORT BEFORE SHARING.` exactly from the generated test image; an unrelated supplied caption was excluded. This is an acquisition check, not a factual-classification test |
| Live response binding | Real text/image API responses passed the rebuilt extension result validator |
| Final readiness endpoint | `/ready` returned true with MariaDB and classifier hash `c2d7df1c519c4022c395a29e1d469e3089452fa8a9b6a15a2079eaa0216ea376` |

Private live records: `tmp/REFINEMENT-LIVE-20261112.json` and `tmp/REFINEMENT-FINAL-20261112.json`. Browser screenshots are private under `tmp/admin-browser-1794421345102/screenshots/`. These tests did not create participant ratings or approve survey items.

## Important unresolved accuracy findings

The exact English sentence `Drinking enough water helps prevent dehydration.` returned **Potentially Misleading**, with P(Misleading) **0.8697065488818485**, through the live API with retrieval disabled. This is a source-supported false-positive sanity case: [CDC water and healthier drinks](https://www.cdc.gov/healthy-weight-growth/water-healthy-drinks/) states that drinking water can prevent dehydration; [NHS dehydration guidance](https://www.nhs.uk/conditions/dehydration/) states that regular fluid intake reduces the risk and includes water as an option. This inspection did not change the model or insert a special-case override for the sentence. A passing integration test is not an accuracy pass.

The live P1.4-billion/3,174-box vape query returned a Philstar URL, but the server could not read the article. The final live lookup reported zero readable sources. Its link is therefore unverified and does not establish a supporting verdict. A readable source for that exact claim was not established in this run.

The prior [speech improvement record](SPEECH-IMPROVEMENT-20261112.md) remains valid: 53 to 50 word errors on the fixed 16-clip sample, with known wording errors still present in the original GMA video. This turn did not retrain ASR or mark that transcript accurate.

Software refinements are applied; classifier generalization, full transcript fidelity, live installed Chrome/Facebook testing and external deployment validation remain open. No “all outputs correct,” new classification accuracy, zero-false-positive, participant-survey or full defense-ready claim is made.

## Loading this build

The backend is already restarted. In the user's installed Chrome, reload SuriPH at `chrome://extensions`, confirm **1.3.17**, then refresh the Facebook tab. The local dashboard remains at `http://127.0.0.1:5173/`; use System status → Refresh status after service changes.
