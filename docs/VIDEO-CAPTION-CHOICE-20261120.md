# Video acquisition choices — 20 November 2026

Installed extension version: **1.3.48**.

One primary click on a video post now attempts direct video acquisition. The
previous initial media chooser is skipped for video posts. Image and text
workflows retain their existing behavior.

When direct video access is unavailable, the result window offers:

- **Caption only** — screens the complete caption without downloading, playing,
  extracting or transcribing the video. Blank, collapsed, URL-only, hashtag-only
  and bare WATCH/LOOK prompts cannot enable this choice.
- **Caption and video** — captures the selected video from its beginning at
  normal speed, then uses the actual extracted speech and eligible frame text.
  The existing transcript review step is retained before classification.

If speech fails the existing quality checks, a complete informative caption may
be used as a scoped fallback. A transcription-provider outage, decoding error or
incomplete caption does not silently become a caption prediction. If the post
or selected video changes while the user chooses, the request is rejected.

Caption-only results keep the standard result layout. About this post and the
expandable Text checked section identify the caption basis. They do not claim
that the video audio or frames were analyzed. Scores, sources and the seven
linguistic features belong to the exact text that was actually classified.

## Validation

- **113** backend/media/API/deployment checks passed.
- **45** extension checks passed; product contract and production build passed.
- **6** isolated Chrome UI scenarios passed, including both choices, actual
  local playback capture, transcript confirmation, quality fallback, provider
  error, changed-post rejection and disabled generic captions. API responses in
  this UI replay were controlled fixtures; it is not a factual-accuracy test or
  inspection of the installed extension on Facebook.
- A live request to `/analyze/video-caption` completed in **0.086 seconds** with
  source lookup off, no video upload, and `transcript_status=not_requested`.
  This single measurement is not a response-time guarantee when sources are on.

The live ASEAN-caption replay still returned Potentially Misleading. The
classifier's known caption false-positive issue remains unresolved. This change
improves acquisition choices and response scope; it does not establish factual
accuracy or survey/defense/deployment readiness. No model, dataset, threshold or
classifier policy was changed.

Reload the unpacked extension in Chrome and refresh Facebook before testing.
The API was restarted with the new route and reported ready.

Original edited files are backed up in
`.run/video-caption-choice-backup-20261120/`.
