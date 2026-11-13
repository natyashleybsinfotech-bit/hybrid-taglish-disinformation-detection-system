# SuriPH finishing status — 2 November 2026

This is the current verification handoff. It does **not** sign off factual
accuracy, resolve the reported false positives, or authorize public deployment.
Preserve the two existing public labels and the pinned hybrid classifier.

## Latest follow-up: evidence disclosure and video text

The user explicitly chose to retain the model prediction when sufficient
claim-specific evidence is missing, **with an unmistakable unverified notice**.
This is not a third prediction label. Both public labels now carry that notice
in English and Tagalog whenever the decision follows the screening model. The
API includes `verification_status: not_verified` for that case. An evidence
assessment is reported separately; none of these changes guarantee zero false
positives. The unresolved vape example below remains an unresolved model case.

Extension **1.3.15** separates caption, speech transcript, image text, and sampled
video-frame text. The exact combined classifier input remains expandable. A
source URL remains clickable even if its article title is inaccessible.

Media changes:

- Speech uses transcription rather than translation, disables previous-text
  conditioning, and enables Whisper's word timing/silence-handling options.
  See [the upstream implementation](https://github.com/openai/whisper/blob/main/whisper/transcribe.py).
- Digital silence is not sent to Whisper. Nonempty speech segments require
  finite timestamps and quality diagnostics: average log probability >= -1.0,
  no-speech probability < 0.60, and compression ratio <= 2.4. Repeated loops
  and missing diagnostics are rejected. A failed segment blocks classification
  of that uncertain transcript instead of silently removing spoken content.
- Image OCR retains scored detections >= 0.60 with readable characters;
  unscored, non-finite, low-confidence and symbol-only detections are excluded.
  Exclusions are disclosed. These thresholds are safeguards, not a calibrated
  guarantee of word accuracy; valid text can also be missed.
- The frame budget is spread over the clip's full duration, rather than only
  the first nine seconds. Three sampled frames do not establish complete video
  understanding. Source text is not autocorrected, summarized or fabricated.

Latest verification: **112 backend tests passed**, extension contract/build
passed, and ten real-component English/Tagalog/narrow-layout views rendered
without horizontal overflow. The media layouts were visually inspected,
including the formerly missing source link and separate speech/frame sections.
These are controlled local views, not a logged-in Facebook rehearsal.

`MEDIA-QUALITY-20261102.json` records real processing of a cached synthetic spoken
clip: its complete English reference was recovered with word error rate 0.0.
A separate silent clip produced an empty transcript and retained its visible
frame text. This is **not** measured natural Filipino/Taglish transcription
accuracy. A representative original video plus a checked transcript is still
needed to measure that. The local API was restarted with these fixes; the live
video request evidence is under `tmp/verification-20261102-media/`.

To use the new UI, reload SuriPH **1.3.15** in `chrome://extensions` and refresh
the Facebook tab. Preserve the existing classifier, threshold and database.

## Changes made in this pass

- Fixed the evidence gate treating `not false` as contradiction. Quoted and
  attributed statements are screened before interpreting a debunk marker.
- Required complete token boundaries when comparing an article assertion.
- Fixed article HTML parsing around void elements such as images and line
  breaks, matching closing tags, and paragraphs outside the selected article.
- Added a bounded reader for the Bureau of Customs' actual UIkit layout. Its
  displayed heading must match its document title; only the following article
  panel is extracted. Navigation, related cards and footers are excluded.
- Added regression coverage for these failures. No model weights, threshold,
  labels, credentials or existing database records were replaced.

## Verification actually completed

- **103 backend tests passed.** Run from the backend directory, or set up the
  import paths using the test discovery command in START_HERE. This restricted
  execution environment initially could not clean temporary directories;
  rerunning with TEMP/TMP under the project's ignored tmp directory passed.
- Dashboard lint and production build passed.
- Extension product-contract checks and production build passed, version 1.3.14.
- Three saved candidate regression cases passed fresh raw-text inference. This
  establishes reproducibility for these cases, not factual correctness.
- MariaDB started; migration returned available with no pending versions.
- The local API was restarted with the fixes. `/ready` returned true, MariaDB
  available, the pinned candidate hash and threshold 0.4000000000000001.
- Actual administrator login, system-status access, decision-history access and
  logout returned HTTP 200. Decision records were present. Credentials were not
  printed or changed. This is API verification, not a dashboard visual rehearsal.
- The new isolated Edge Facebook harness attempt did not complete: its browser
  debugging endpoint was unreachable and the attempt was stopped. The older
  fixture report remains historical; no logged-in Facebook test passed here.

## Live replay: the reported vape example remains unresolved

The caption used here was reconstructed from the user's screenshot, **not**
captured from the original extension request. Its punctuation and concatenation
must not be mistaken for a byte-identical replay of that request.

With source lookup enabled, the live model score was **0.9864678225697466** and
the final label remained **Potentially Misleading** before and after the reader
fix. There was no threshold change or forced override.

Before the fix, this official URL was returned but marked inaccessible:

https://customs.gov.ph/biggest-illicit-vape-haul-worth-%E2%82%B11-4-billion-crushed-as-boc-intensifies-crackdown-on-illegal-trade/

After the fix, it was readable, with its own article heading and nine paragraphs,
including the 3,174-box detail. The gate still assessed it as related because it
does not find the complete submitted caption as a matching assertion. Another
result concerned a different monetary amount and was inaccessible to the reader;
it must not be counted as corroboration.

**The source reader is repaired for this layout; the classification complaint is
not resolved.** The present exact-assertion gate does not perform general
paraphrase/claim verification, and different hosts/bodies do not establish
independent corroboration. Do not describe it as a verified fact-checker.

Private execution evidence is under `tmp/verification-20261102/`:
`backend-tests.log`, `live-readiness.json`, `admin-live.json`,
`reported-caption-live.json`, and `reported-caption-after-reader-fix.json`.
Do not publish the temporary files or secrets as part of a broad Git add.

## Remaining work before a factual-performance sign-off

1. Resolve claim/evidence matching against the original failed inputs, including
   paraphrases, multi-sentence captions, quotations, changed numbers and dates,
   and sources reporting different stages of an event. Evaluate any proposed
   decision change on a separate evidence-reviewed batch; do not tune to these
   reported examples or equate missing evidence with falsehood.
2. Run the current unpacked extension on actual Chrome/Facebook and record the
   selected post, exact submitted text, matching article and final result. Verify
   stale-response/post-switch handling and the eight-part bilingual display.
3. Complete independent review of the already prepared evaluation batch and
   report errors and unresolved cases honestly. Keep ISO usability surveys
   separate; software-test passes are not a substitute for factual labels.

The local API and MariaDB were left available for this rehearsal. No hosting,
Chrome Web Store publication, retraining, model replacement, Git commit or push
was performed in this pass. Existing unrelated/uncommitted work was preserved.
