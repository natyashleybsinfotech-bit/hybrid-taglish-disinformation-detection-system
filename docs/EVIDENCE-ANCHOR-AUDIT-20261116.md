# General evidence-gate audit — 16 November 2026

Status: **not a claim of survey/deployment readiness**. The current Mariah Deborah Facebook failure has not been reproduced because the exact submitted text and returned quotation were not available in the attachments. The screenshot proves that the deterministic post-LLM guard rejected an assessment, but does not reveal which material anchor was rejected. No Mariah-specific label override was added.

The user's concern is valid: a successful replay of one post does not establish reliability on subsequent posts. The previous ASEAN replay remains a single integration case.

## Confirmed general defect

The location guard compared raw place strings. A synthetic supported Taglish claim using `sa Maynila` was rejected when its English evidence said `in Manila`. The fix normalizes a bounded set of explicit Filipino/English city-name equivalents. It does not remove location checking: the same audit still rejects a claim saying Cebu when the quotation says Manila.

## Diagnostic correction

Rejected assessments now expose `validation_issues` for people, quantities, amounts, event dates, years and locations. English and Tagalog explanations both describe the failed comparison; the prior code could retain a positive Tagalog LLM explanation while the English guard rejected it. No private input or credentials were added to server logs. These diagnostics travel in the normal user-request response.

## Verification

- Nine declared synthetic deterministic-gate cases: **9/9 passed after the fix**, versus 8/9 beforehand. These cover name capitalization, Taglish place equivalence, date abbreviation, number spelling, a song title, changed quantity, changed city, changed date and changed named person. This audit mocks the LLM assessment; it is not a real-world accuracy evaluation or a test of Gemini's own reasoning.
- **250 backend tests passed**, including a regression checking that wrong-place rejection is consistent in both languages.
- No model training, classifier change, threshold change, source-count relaxation or Mariah-specific override.
- Secret-free backup: project `runtime/anchor-audit-backup-20261116T014931/`.

## Outstanding

The exact Mariah caption and quotation are still necessary to determine its specific rejected field and to verify an actual fix for that case. Current generic single-secondary-publisher sufficiency rules also remain in effect: an assessment being eligible does not automatically mean there is enough evidence to change the final label. Do not describe this audit as eliminating all false positives or as completing image/video testing.

The current Chrome view was inspected read-only; the Mariah result was no longer open, so its original text could not be recovered from that current view. No Facebook content was posted or modified.
