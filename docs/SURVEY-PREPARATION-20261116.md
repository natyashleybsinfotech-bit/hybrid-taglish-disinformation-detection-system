# Survey preparation — 16 November 2026, SuriPH 1.3.43

## Completed
- Result cards preserve the SuriPH banner, two English labels, short explanation, post context, expandable analysis details, sources, exact text, reminder and check-again flow. Provider branding was removed from result copy; actual Google Gemini / Serper processing remains disclosed in an expandable privacy notice before checking. Internal provider metadata stays truthful for debugging; no claim of a custom trained classifier was substituted.
- No fabricated model confidence or linguistic measurements were added. Existing model-mode details are unchanged. Unverified predictions remain clearly identified; source availability does not automatically prove a claim.
- History now stores unscored classifier decisions. Schema 7 changes only ScreeningDecisions.model_score nullability. The admin displays Not available for null scores, not 0.000. Before migration, a full local SQL backup was created. All 4,038 existing history rows had identical count and full-row digest before/after. See workspace outputs/SURVEY_HISTORY_MIGRATION.json for the backup path and verification.
- 267 backend tests passed, including migration of a legacy SQLite table with old-row preservation and new null-score persistence. API unit decision inserts are now mocked so those tests do not write into the user's live history.
- 38 extension behavior tests passed; extension and admin production builds passed; admin lint passed.
- Isolated MariaDB 11.4.13 provision/migrate/idempotence, limited runtime privileges, rollback, restart and logical backup/restore checks passed at schema 7. The existing database was not used for that harness.
- Three live API checks passed and were read back from MariaDB: linked GMA rice suspension -> supported Non-Misleading (4039); opposite claim -> contradicted Misleading (4040); opinion without source lookup -> unverified Non-Misleading (4041). Scores are NULL and stored final labels match returned labels.
- Twelve real-component layout renders passed. English and narrow Tagalog result HTML contain neither Gemini nor DistilBERT branding. The privacy disclosure remains in the input view. Screenshot reviewed: docs/verification/ui/popup-result-en.png.
- Final isolated Facebook-origin modal rehearsal passed on 1.3.43: chooser/image/video options, exact caption scoping, post-switch binding, stale responses/reload, eight-part order and bilingual switching. The first run caught a disclosure helper-scope error; it was fixed and a fresh run passed. Its old failing process exited. This is an isolated Edge fixture, not the user's Chrome/Facebook account.

## Survey decision
The revised UI and local API are prepared for a supervised pilot. Full questionnaire/survey sign-off is STILL PENDING; software passing does not establish extraction accuracy or participant acceptance.

Remaining concrete gates:
1. Reload SuriPH in the actual Google Chrome extensions page, refresh Facebook, and verify one complete text, image and video check in the installed extension. Computer Use could read the existing Facebook window but could not click its Extensions tab: coordinate input geometry is unavailable. Therefore this live installed-build check was not completed here.
2. Compare the selected image's actual words with OCR and the complete original video speech with the transcript. The prior 45-item record had a failed transcript-matching item (1.4); this UI/database change does not repair or retest ASR. A controlled media chooser test is not evidence of accurate transcription.
3. The current questionnaire's model-score and linguistic-feature items (4.4/4.5 in the acceptance mapping) describe the older hybrid display. This Gemini mode has no calibrated score or displayed hybrid feature measurements. Keep those items not demonstrated / N/A until the instrument and actual mode agree; do not rate missing functionality as observed. No questionnaire content or responses were edited in this task.
4. Plan quota and session scheduling before inviting 60 respondents. Current application limits remain one active provider request, 4 requests/minute and 100/day, plus Google's own quota. At three uncached checks per participant, 60 sessions need 180 calls, exceeding a single day's application cap. No paid billing or silent cap increase was enabled. Native Google Search remains quota-blocked/off; existing Serper/article reading supplies evidence.

## Start and rollback
The local API is running in Gemini mode on 127.0.0.1:8000 with MariaDB. This is not a public deployment. If restarting, run scripts/start-mariadb.ps1 then scripts/start-gemini-trial.ps1 from the project root. Do not use start-original-model.ps1 unless intentionally returning to the hybrid classifier.

Reload Chrome's installed SuriPH to build 1.3.43 and refresh Facebook before evaluating; a saved previous result is not a new check.

UI/code backup: runtime/survey-ui-backup-20261116. The original pinned model file remains intact. For classifier rollback, set SURI_SCREENING_MODE=model and use start-original-model.ps1; schema 7 remains compatible with older numeric-score writes. Do not restore the pre-survey SQL backup over new participant records just to roll back UI code.

## Records
Project: docs/SURVEY-BUILD-20261116.json, docs/UI-VERIFICATION.json, docs/FACEBOOK-MODAL-VERIFICATION.json and docs/MARIADB-VERIFICATION.json.
Workspace outputs: SURVEY_UI_BACKEND_TESTS.log, SURVEY_HISTORY_MIGRATION.json, survey_ui_api_20261116/CHECKS.json and history-checks.json.

This report supersedes the previous primary-trial note only on provider-neutral UI and the now-resolved history-storage limitation. It does not certify factual accuracy, survey validity, zero false positives, or production deployment readiness.
