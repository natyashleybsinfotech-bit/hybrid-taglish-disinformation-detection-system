# Primary Gemini local trial — 2026-11-16

## Active behavior
The local API is running in SCREENING_MODE=gemini with gemini-3.5-flash-lite. /ready reports MariaDB available and hybrid_classifier_active=false. This readiness check verifies configuration and database connectivity, not provider availability or factual accuracy.

Google Gemini is the primary classifier for confirmed text, including the text delivered by existing image/video extraction. The hybrid classifier is not initialized at startup or called by the Gemini analysis path. The two public labels are unchanged. No retraining, model deletion, paid-plan activation, or database reset occurred.

Existing Serper retrieval and server-side article reading supply sources. Gemini returns source passage IDs; the server supplies original passages and applies existing material-detail/conflict checks. Merely finding a related link does not establish support. Insufficient evidence still returns the Gemini prediction clearly marked not_verified, as requested. Provider failures return an error/retry response with no fallback label. No calibrated confidence percentage is invented.

Native Google Search grounding was actually tried and returned HTTP 429 quota errors on both source-backed and no-source requests, with a further diagnostic confirming Google's quota response. It is therefore disabled explicitly (SURI_GEMINI_SEARCH_GROUNDING=false). Existing Serper article search remains available. No billing settings were changed. Native Search is implemented but NOT live-validated as successful.

## Validation
- Final backend suite: 266/266 passed, including no-hybrid fallback, provider failure, source-passage contract, and reuse of a validated assessment without a second reader call.
- Extension behavior tests: 38/38 passed. Production build succeeded; manifest 1.3.42.
- Three direct provider checks without native Search completed: readable CDC hydration support; false antibiotics/viruses statement; unverified opinion. All produced the expected labels. These are diagnostic examples, not an accuracy estimate.
- Three actual local API checks completed: GMA-linked suspension of P20 rice sales -> Non-Misleading / evidence_assessed; opposing sales assertion using the same article -> Misleading / evidence_assessed; opinion without lookup -> Non-Misleading / not_verified. All scores remained null and none used the hybrid classifier.
- Actual supported API response was rendered using the real popup components in English and narrow Tagalog. Twelve layout renders passed (additional flagged/media/evidence views use controlled fixtures). Screenshot reviewed: docs/verification/ui/popup-result-en.png. No installed Chrome/Facebook end-to-end verification is claimed.
- Original model SHA256 unchanged: 72d87971ee2af7fca1f6f0a9b94bbe92618bd92ce8c5e48e35b80882e1321c7c.

## Trial boundaries
This is a reversible LOCAL TRIAL, not a defense/survey/deployment sign-off. It does not establish real-world Taglish accuracy or guarantee zero false positives. Existing OCR/audio extraction was not replaced or independently revalidated by this classifier change.

The legacy screening_decisions table requires a numeric model score. Gemini has no such score. To avoid storing a fabricated value or changing schema during this trial, legacy decision-trace insertion is explicitly skipped: decision_record_status=not_recorded_llm_trial. Do not expect these trial checks in that admin history. Other existing admin data is preserved. Persistent Gemini decision history needs a separate compatible schema change before production.

The existing provider limits remain 4 requests/minute and 100/day, plus Google's own quota. Gemini timeout is 30 seconds; quota or outage can still prevent an answer. Native Search references, when enabled later, are distinct from validated article passages.

## Try it
1. In Chrome extensions, reload SuriPH (built version 1.3.42).
2. Refresh Facebook and perform a new check rather than reusing a saved result.
3. Keep source lookup enabled to retrieve readable articles. Inspect exact text and matching passages.

Start the trial from the project root:
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-gemini-trial.ps1

Do not use start-original-model.ps1 for this trial: it deliberately selects the original classifier. Private .env.local currently selects gemini and retains the existing API key and database credentials; no credentials are included in this report or backup.

## Rollback
Stop only this project's API, change SURI_SCREENING_MODE=model in backend-api/.env.local, and run scripts/start-original-model.ps1. Original model assets remain intact. Secret-free pre-change code backup: runtime/primary-gemini-backup-20261116T134759. Native Search default is off. Production configuration validation still rejects this local trial mode.

## Evidence files
Workspace: outputs/PRIMARY_GEMINI_TESTS.log; outputs/primary_gemini_trial_20261116 (failed native grounding probes); outputs/primary_gemini_article_trial_20261116 (non-grounded direct checks); outputs/primary_gemini_api_20261116 (live response JSONs and final-ready.json). Project UI report: docs/UI-VERIFICATION.json. The direct probe name native_search in the non-grounded article folder is a reused case name: grounding_requested=false; it was not a successful native Search request.
