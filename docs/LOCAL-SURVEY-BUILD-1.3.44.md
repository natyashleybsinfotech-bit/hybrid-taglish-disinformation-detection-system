# Local survey build 1.3.44 — 16 November 2026

## Delivered
The current user choice is local laptop survey operation, not VPS or public deployment. The API and MariaDB are running locally. Production deployment guards were not weakened or bypassed.

SuriPH result cards no longer display Google/Gemini branding or an empty Google Search section. Result content remains the submitted claim, explanation, source cards, exact checked text and reminder. Processor identities remain accurately disclosed inside the expandable privacy/data-processing notice before checking. News source names and actual claim quotations are not censored. Internal provider metadata remains available for diagnostics. This is a SuriPH presentation cleanup inspired by the requested reference, not a claim that Tunai source code/backend was copied or inspected.

The user chose Gemini-generated scores instead of returning to the original hybrid classifier. Gemini now returns a required integer self_reported_score from 0 through 100 in its structured response. Missing, string, boolean, fractional or out-of-range scores reject the provider response; no default percentage is inserted. Prompt requests an honest subjective estimate rather than a fixed high value. The original hybrid is still not initialized/called in this mode.

The public UI labels it AI-reported confidence and identifies which initial prediction it belongs to. It explicitly says it is the AI's own estimate, not measured accuracy or proof that a claim is true/false. Evidence status remains separate. If source validation changes the final label, the score is not inverted or relabeled: a notice explains that it belongs to the initial prediction. Old hybrid model_score remains NULL; calibrated final_confidence remains NULL. No score threshold was added to the evidence decision logic.

## Validation
- 272 backend tests passed: provider score validation, no hybrid fallback, source evidence guards, score preservation after a changed final label and old/new database persistence.
- 39 extension behavior tests passed; extension production build succeeded.
- Admin lint and production build passed. Admin history shows the separate self-reported score and its label, while old hybrid scores remain in their own field.
- Schema 8 adds only nullable ai_reported_score and ai_reported_label columns. A private SQL backup preceded migration; all 4,047 existing history rows retained identical count and pre-existing field digest. SQLite legacy-table rebuild also preserves old rows when adding these new columns. Isolated MariaDB schema 8 migration, runtime DDL denial, restart and logical backup/restore passed.
- Three actual API checks passed and scores/labels were read back from history: linked GMA rice suspension, Non-Misleading / evidence_assessed / AI score 100; opposite assertion, Misleading / evidence_assessed / AI score 100; opinion with lookup off, Non-Misleading / not_verified / AI score 50. These are actual provider outputs, not system accuracy statistics.
- Twelve component layout renders passed, including English and narrow Tagalog. The actual supported result screenshot was inspected. Result HTML for these cases has no Google/Gemini text and no empty grounding block; the input privacy disclosure still identifies external processors.
- Final isolated Facebook modal rehearsal passed on 1.3.44, including AI-score rendering assertions, real explanation paragraph, post binding, two-label output, image/video chooser, source-only refresh and language switch. An initial rehearsal exposed an undefined in-page displayLabel call; it was corrected to use the bound local label, rebuilt, and a fresh rehearsal passed. The failed run is not counted as a pass. This is isolated Edge, not the user's installed Chrome/Facebook account.
- start-survey-local.ps1 syntax and already-running-API branch passed: no duplicate server was launched.

## Use locally
1. From the project root, run: powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-survey-local.ps1
2. Wait until API startup and engine preparation finish. Keep that terminal running when it starts the API. Engine preparation took ~74 seconds under the current busy workstation load, compared with ~9 seconds in the earlier isolated run; no constant startup time is promised.
3. In chrome://extensions, reload SuriPH version 1.3.44, then refresh Facebook. Make a NEW check: previous cached browser results do not acquire a newly generated score.
4. Keep source search enabled for evidence-backed checks. Review extracted image text and actual spoken transcript before confirming a media check.
5. The extension-only ZIP is available as SuriPH-local-survey-1.3.44.zip in this chat workspace outputs. It contains dist files and manifest.json at ZIP root, not server credentials/models/private data. For a new installation, extract it and use Load unpacked on that extracted folder. Existing installations should reload their current dist folder instead of installing a duplicate.

## Survey boundaries still pending
Run a supervised pilot using the actual installed Google Chrome build before collecting the full survey: one complete text post, one image and one video; compare extraction with originals, verify the matching source passage, language switching, score explanation, and that each result belongs to the selected post. Actual Chrome control remains unverified after the earlier computer-control geometry failure. No new real-account pass is asserted.

Prior transcription accuracy problems are not solved by a score or UI change. The 69-second GMA benchmark remains review_required with known material-word errors despite faster extraction. The separate video-speed report documents the one-clip 85.4 -> 62.1 second extraction measurement and repeat cache behavior, excluding Facebook acquisition and source checking.

Current local limits remain one active provider request, four/minute and 100/day, plus Google's own quota. Stagger survey sessions. Sixty respondents making three uncached checks each require 180 provider calls and exceed a single day's application cap. No cap increase, billing activation, native Search quota workaround, or public exposure occurred.

Questionnaire/video/manuscript wording must describe the current mode. The old hybrid Misleading-class probability and seven linguistic metrics are not being produced by this Gemini mode. This new score is uncalibrated self-reported confidence; it cannot substitute for the old held-out model accuracy or support an accuracy claim. Questionnaire items evaluating missing metrics remain not demonstrated/N/A pending instrument alignment. No questionnaire, manuscript or video content was edited in this task.

## Evidence and rollback
Pre-change source backup: runtime/ai-score-backup-20261116. Backup/migration details: workspace outputs/AI_SCORE_MIGRATION.json. Live response/history proof: outputs/ai_reported_score_api_20261116. Unit log: outputs/AI_SCORE_TESTS.log. UI/modal/MariaDB verification reports remain in docs.

To return to the previous score-free version, restore the backed-up code/client and rebuild; schema 8 is backward-compatible and may remain in place. Do not restore a pre-survey SQL dump over new participant records merely to revert UI. Original pinned model assets were preserved. No public-deployment or complete-survey-readiness certification is claimed.
