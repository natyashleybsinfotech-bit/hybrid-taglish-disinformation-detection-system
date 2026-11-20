# Local system retest — November 18, 2026

Most automated functional checks passed. This is not an all-clear for survey or deployment.

- Backend: 291 tests passed with the normal pytest command after isolating private runtime configuration. Initial run had 33 failures caused by trial settings being loaded by tests; these are retained in REPORT.json.
- Extension: 40 behavior tests, video-review contract and product contracts passed. Extension build and dashboard lint/build passed.
- Admin: isolated Chrome login, cookie reload, logout revocation, viewer restrictions, and desktop/narrow layout checks passed.
- Extension UI: 12 English/Tagalog component layouts rendered; seven features and separate AI-reported confidence remain visible. Isolated Edge Facebook fixture passed media chooser, caption scope, stale-result binding, source refresh and language-switch checks.
- Live caption replay: prior CNN/Eala caption completed in 6.444 seconds with seven features and a source-backed result. This replay used visible caption text, not an unknown image/video selection or ambiguous short URL.
- Live synthetic image: extracted its actual printed phrase and returned a result in 2.776 seconds, without a supplied caption.
- Live existing 69-second video: full audio extraction/review returned HTTP200 in 16.063 seconds; repeat was cached in 0.064 seconds. This excludes Facebook download/playback capture and human review. No video classification was requested.

## Targeted fixes

Added one bounded transport retry for temporary service/network failures, with metadata-only error diagnostics. Each attempt consumes the existing provider request budget; the retry uses only remaining timeout. Authentication, quota, invalid payload and validation failures are not retried. The original classification, source validation, transcript review, model assets and database schema are unchanged. No fallback prediction is invented.

Added regression cases for recovery, exhausted retries, permanent errors, deadlines, quota protection and private-data-safe diagnostics. Tests no longer read private laptop .env files.

## Remaining blockers

Natural Taglish transcription quality is still not passed. The returned transcript contains unclear phrases, including “maiinm ng idolum”; HTTP200 does not prove accurate speech recognition. Mandatory transcript review is preserved. Current speech/frame agreement and successful extraction do not establish fidelity to every spoken word.

The signed-in Chrome/Facebook flow was not verified: computer inspection reported the existing Facebook window minimized. The isolated Facebook fixture does not substitute for that test.

Closely spaced live checks hit request limits before the paced rerun. The configured budget remains 4 external requests/minute and 100/day, shared by classification and audio. Survey throughput is not established. No billing or quota settings were increased.

MariaDB, API and dashboard are left running locally. Extension remains version 1.3.46; changes in this retest are backend/test-only. No retraining, dataset edits or database reset occurred.
