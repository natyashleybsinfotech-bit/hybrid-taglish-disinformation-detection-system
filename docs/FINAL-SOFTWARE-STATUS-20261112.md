# Current software status — 12 November 2026

**Later extraction update:** [Extraction repair record](EXTRACTION-REPAIR-20261112.md) documents extension **1.3.21**, the current image/video extraction changes, real-media replay, and remaining GMA transcript failure. The version and test counts below describe the earlier 1.3.19 build.

Extension build: **1.3.19**. Changes are local; no public deployment, classifier training, dataset editing, threshold change or model replacement was performed.

## Applied repairs

1. The selected post owns its media and context. Larger videos and links inside nested comments/posts no longer become the selected post's video or references.
2. Browser video recording starts from the beginning at normal speed, restores the original speed, releases captured tracks, and rejects stalled, changed, removed or incomplete captures. Timeout does not submit a partial recording.
3. Delayed source responses cannot restore a cleared popup result or overwrite a newer in-page Facebook result. Source-only refresh preserves classification and already assessed evidence.
4. Public article links require readable fetched bodies that pass relevance checks. Unreadable discovery links are removed; a failed lookup does not imply that the post is false. Person matching now recognizes titled two-word names; conflicting explicit full dates are rejected. Fact-check search results also pass claim relevance checks before their ratings can be displayed.
5. Video frame-reader failure is distinguished from a frame with no readable text. Partial extraction is disclosed before confirmation and in the extracted-text details. Caption, image text, speech and frame text are identified separately.
6. Video extraction, confirmed-video analysis and source lookup now share the existing request/concurrency protections.
7. Deployment preparation requires an explicit model profile. It refuses an unapproved local candidate rather than silently selecting the older historical classifier. Existing approval restrictions remain intact.

## Verified now

| Check | Result and boundary |
|---|---|
| Backend | **148 tests passed**. Private log: `tmp/system-final-refinement-20261112.log`. |
| Extension | **14 result/capture/review checks**, product contract and build passed. |
| Selected-media browser rehearsal | Rebuilt unpacked extension passed the isolated Edge Facebook fixture, including larger nested-video and comment-link exclusion, post switching, eight-part order and source-only lookup. No logged-in Facebook account was tested. |
| Real saved news clip | Actual production capture function recorded the **69.099-second** original at normal speed, starting from a mid-video position. Captured video was processed successfully: speech and frame text extracted in **59.34 seconds**, with three sampled frames. This establishes acquisition, **not word accuracy**. Private `tmp/media-regression/selected-production-extraction-20261112.json`. |
| Actual image API | OCR exactly returned `READ THE COMPLETE REPORT BEFORE SHARING.` and excluded an unrelated caption. The predicted label was not evaluated as factual truth. |
| Live readable sources | Vape query returned the readable Philstar seizure article; dehydration query returned the readable CDC water article. The unreadable unrelated seizure link was excluded on retest. Neither source-only request invoked classification. Private `tmp/FINAL-READABLE-SOURCES-20261112.json`. |
| Popup interface | Actual built extension page passed against the live API in isolated Edge: empty input, duplicate request protection, label/score parity, complete long input, language switching, seven features and eight-part order. The extension page was opened directly; the toolbar action was not verified. Earlier Chrome loading and popup attempts failed and are not counted as passes. |
| Rendered interface | Ten actual React component views rendered in headless Chrome, including English/Tagalog, image/video details and narrow layouts without horizontal overflow. These are visual fixtures, not factual accuracy tests. |
| Admin | Lint/build and actual local dashboard/API login, session reload, logout, expired session and narrow layout passed in isolated Chrome. No participant responses were created. |
| Database | Isolated MariaDB provisioning, schema version 6, idempotent migration, denied runtime DDL, rollback, restart persistence and logical backup/restore passed. The existing working database was not reset. |
| Local load | Five short requests, complete long input and three simultaneous requests returned HTTP 200; dashboard and readiness endpoints returned HTTP 200. This is one workstation run, not a public capacity guarantee. |
| Deployment | Static configuration checks passed. Docker is absent; Linux containers and public TLS were not tested. The static report concerns the explicitly selected historical release template, not approval of the active candidate. |

## Still not completed

- **Speech fidelity:** the real clip still contains incorrect words, including “Nag-high” and a person's surname. Complete capture does not fix decoder wording. Do not present the transcript as verified or use this result to mark the questionnaire's transcript-matching item passed.
- **Classifier factual accuracy:** the active classifier remains unchanged. Existing false-positive diagnostics remain model limitations. The user owns any subsequent retraining; no new training was started here.
- **Actual installed Chrome/Facebook session and public hosting:** the user's installed extension, current signed-in Facebook DOM, chosen server and public HTTPS still require their respective checks. Controlled fixtures do not substitute for them.

Active classifier SHA-256 remains `c2d7df1c519c4022c395a29e1d469e3089452fa8a9b6a15a2079eaa0216ea376`, profile `full-cleaned-20261023T022416Z`, threshold 0.40. No automatic trusted-publisher override, invented transcript, third prediction label or random prediction was introduced.

Reload the unpacked extension from `chrome-extension/dist`, confirm **1.3.21**, and refresh the Facebook tab. API and dashboard remain local. These repairs do not constitute a zero-error, final-defense, survey or public-deployment sign-off.
