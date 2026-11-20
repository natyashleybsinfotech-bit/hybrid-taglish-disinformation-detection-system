# SuriPH Gemini evidence reader — 16 November 2026

> Historical record: the later 20 November local-model migration supersedes any active Gemini/cloud-provider description and cloud timings below. See [current source](CURRENT-SOURCE-20261120.md) and [removal record](GEMINI-REMOVAL-20261120.md). Older results remain preserved as historical evidence.

Implemented and enabled locally using `gemini-3.5-flash-lite`. The key is stored only in the backend's ignored `.env.local`; it is not bundled in the extension. The original classifier remains profile `20261011T235112Z`, threshold 0.65, SHA-256 `72d87971ee2af7fca1f6f0a9b94bbe92618bd92ce8c5e48e35b80882e1321c7c`. No training was performed.

## Behavior

With source checking selected, Serper locates articles. The server retrieves readable bodies, and Gemini compares the entire submitted claim against those bodies. Returned source IDs must belong to the supplied sources; decisive quotations must occur in the supplied body. Material-entity checks, conflicting evidence checks, and the existing scoped-primary/two-independent-publisher rules still apply. Supporting or contradicting sufficient evidence can change the final two-label result. Unavailable, incomplete, insufficient or conflicting evidence retains the classifier prediction as unverified. A related link alone is not proof. Evidence-derived results have no invented confidence percentage.

The English and Tagalog source-check controls disclose the providers. The result shows a bilingual evidence explanation and source passages. The original model score remains separate.

## Verification

- Backend: 242 tests passed (provider disabled for legacy tests; new reader tests use mocked provider responses).
- Extension: 34 behavior tests passed, product contracts passed, production build passed; version 1.3.40.
- Live Google provider: connection/generation succeeded; three declared synthetic article fixtures passed (supporting paraphrase, explicit contradiction, incomplete support).
- Live API plus real retrieval: hydration claim retrieved the CDC article `https://www.cdc.gov/healthy-weight-growth/water-healthy-drinks/index.html`; Gemini returned a literal supporting passage, and final result became No Misleading Information Detected. Original model result remained recorded separately as Potentially Misleading.
- Local `/ready`: true, MariaDB available, original classifier hash verified. `/health`: Gemini enabled and configured.
- Twelve isolated-browser layouts passed, including English/Tagalog, narrow popup, evidence, media and admin login. Screenshot inspection confirmed the actual live API explanation rendered correctly.

Evidence: `LIVE_API_CHECK.json`, `LIVE_READER_CHECKS.json`, `ACCESS_CHECK.json`, `GENERATION_CHECK.json` in this folder. Project logs: `tmp/gemini-backend-tests-20261116.log`, `tmp/gemini-extension-tests-20261116.log`, `docs/UI-VERIFICATION.json`.

## Limits and next use

This does not establish real-world accuracy, eliminate all false positives, validate current video transcription, or certify public deployment. Installed Chrome/Facebook end-to-end testing remains required. Reload extension 1.3.40 from the existing `chrome-extension/dist` folder, refresh Facebook, keep source checking selected, and run a fresh analysis (an old result is not automatically reclassified by a source-only refresh).

Limits: 20-second provider timeout, one concurrent request, 4 provider requests/minute and 100/day, 5-minute successful-assessment memory cache. These are local single-worker safeguards, not billing guarantees. Rate limits and provider failures retain the unverified classifier fallback. The current API startup script uses one worker. Image OCR and video speech extraction were not modified by this integration.

## Rollback and credentials

Secret-free original-file backup: `runtime/gemini-backup-20261116T011739/RESTORE_MANIFEST.json` under the project. To disable only the new reader, set `SURI_GEMINI_ENABLED=false` in the private backend `.env.local` and restart with `scripts/start-original-model.ps1`. This re-enables the pre-existing lexical evidence path; it does not restore all files. Full file restoration should use the manifest, preserve unrelated changes, and rebuild the extension. No database reset is needed.

The temporary workspace key copy was removed after configuration. Since the user supplied the key in chat, replace it in Google AI Studio and update the private backend setting before public deployment; do not paste the replacement into chat or source control.
