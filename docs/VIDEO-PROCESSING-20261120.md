# Video processing update — 20 November 2026

The installed implementation keeps one transcription request for the complete
decoded audio. While that cloud request runs, a separate worker reads the same
sampled video frames. Frame relevance filtering still uses the completed speech
transcript. Local CPU Whisper remains sequential to avoid competing CPU work.
The OCR reader now warms at API startup.

## Measured result

One live serial-then-parallel comparison used the same 69.12-second recording,
captured in an isolated Chrome window from the existing local news fixture.

| Measurement | Serial | Parallel |
|---|---:|---:|
| Upload and extraction to review response | 13.468 s | 9.101 s |
| Complete-audio transcription | 7.271 s | 8.621 s |
| Frame OCR work | 5.728 s | 7.582 s |

The measured extraction reduction was 4.367 seconds (32.43%). The concurrent
stage durations overlap; they must not be added to estimate total time.
The same sampled frames, OCR text and OCR regions were returned. Neither
extraction used the extraction cache. Cloud response latency varies; this single
comparison does not establish a general speed percentage or transcript accuracy.
The transcript wording varied between requests and still requires user review.

Input SHA-256:
`5a08bf9531bd55dbbe7c2de95d9ef457d5db94605a5228f8c7ed0d36af55bcca`

The measurements exclude real-time playback, final classification and source
lookup. If direct download is unavailable, the complete selected video still
needs normal-speed playback. A 69-second capture is not a 9-second check.

## Validation and scope

- Final backend/media/API/deployment checks: **109 passed**.
- Final extension checks: **41 passed**, plus product contract and release build.
- New concurrency checks confirm OCR starts before cloud speech completes and
  the worker is joined before temporary files are removed on speech failure.
- Isolated Chrome capture, actual FFmpeg decoding and actual cloud transcription
  were exercised. The installed extension on Facebook has not been inspected in
  this run; this was an isolated local replay and direct API rehearsal.
- Build version: **1.3.47**. Reload the unpacked extension and refresh Facebook.
- The privacy notice was corrected: local classification and optional cloud
  classification/transcription are described separately.

An experimental capture-time transcript reuse path was also measured. It saved
only 0.205 seconds in the final ASR step and repeated a boundary phrase. It was
removed from the installed runtime. Its source and test records remain in the
workspace trial folder for review; no experimental endpoint or prefix uploads
remain in the final extension flow.

The DistilBERT classifier, training data, threshold and evidence policy were not
changed by this video update. Previously reproduced caption false positives
remain unresolved. This update does **not** establish survey, defense or
deployment readiness, or factual accuracy of future predictions.

Original changed files are backed up under
`.run/progressive-video-backup-20261120/`. That private backup includes the old
local environment file and must not be included in a public release package.
