# Video mismatch review and source-result clarification — 13 November 2026

## What changed

`POST /analyze/video` no longer returns a classification when extraction marks
`speech_frame_agreement` as `review_required`. It returns the extracted speech
and sampled-frame text for review without a prediction. The Facebook extension
routes that response into the existing review panel; classification continues
only after the user confirms the displayed text. Videos without a detected
mismatch keep the direct-result flow.

The result explanation now distinguishes three cases that can otherwise look
like contradictory evidence:

- Readable sources both supporting and contradicting a claim leave an unresolved
  conflict; the model label remains unverified.
- A source can directly support a claim but still fail the trusted-source
  threshold. One readable trusted source is sufficient under the current policy
  when it supports all material claim details and no readable source contradicts
  it; otherwise multiple independent sources or a primary source are required.
- Related coverage, search previews, and inaccessible articles are not proof of
  the complete claim.

This preserves the two public labels. A label is not a factual verdict, and
neither a related link nor a model score establishes truth.

## Verification and limits

- Full backend suite: **186 passed**.
- Extension behavior tests: **20 passed**.
- Extension product and video-review contracts passed.
- Production extension build passed; its manifest reports **1.3.28**.
- Local `/ready` returned true with MariaDB and the configured local-trial
  classifier. This does not establish deployment approval or factual accuracy.
- A 62-second eGov video extraction took **165.848 seconds** on this
  workstation's CPU in the latest recorded retest. Speech recognition can still
  mishear Taglish or names; text/frame agreement only catches some mismatches.
  A matching but incorrect transcript can still proceed to classification.
- The GMA news-video example retains material speech-recognition errors.
  Questionnaire item 1.4 remains failed, and natural Taglish/news-video
  accuracy has not been established.

The current UI flow has not been manually observed in the user's installed
Google Chrome/Facebook session. After rebuilding, reload the unpacked extension
from `chrome-extension/dist` and refresh the Facebook page before rehearsing.
