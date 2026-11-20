# Video extraction speed update — 16 November 2026

> Historical record: the later 20 November local-model migration supersedes any active Gemini/cloud-provider description and cloud timings below. See [current source](CURRENT-SOURCE-20261120.md) and [removal record](GEMINI-REMOVAL-20261120.md). Older results remain preserved as historical evidence.

## Applied and running
- Per-stage backend extraction timings: audio decode, frame sampling, speech-engine lookup/load, language detection, transcription, frame OCR and extraction total. Review responses and confirmed video results expose these as diagnostic metadata; the result UI is unchanged.
- Startup warm-up in scripts/start-gemini-trial.ps1 loads the existing configured speech and OCR engines in the SAME API worker before accepting checks. Latest measured warm-up: 8.665 s (speech 4.064 s; OCR 4.601 s). This moves first-use loading into preparation; it does not eliminate processing time or load engines in a disposable separate process.
- Short-circuit language detection: long clips still need all three English probes at probability >=0.95 to choose automatic English decoding. Once a probe fails that predicate, remaining probes cannot affect the Filipino-hint decision and are skipped. No acceptance threshold, sample duration, speech decoding, retry rule or quality gate changed. Strong all-English clips still run three probes.
- A successful complete extraction may be reused for the exact same bytes, suffix and extraction settings. Fingerprint includes engine/model, language, OCR/quality settings, frame limits and pipeline revision. Only extraction is cached; predictions, evidence lookup, post captions/context and review tokens are NOT cached.
- Cache is in worker RAM only: maximum 2 entries and 1 MiB of serialized extraction data, valid 10 minutes by default (bounded configurable TTL). Expiry timers remove entries even without another request. No uploaded video bytes are retained in this cache or written as cache files. Failures and partial OCR extractions are not cached. Callers receive detached copies so edits cannot contaminate a later review. Restart clears it.

## Full-video measurement
Existing regression clip: facebook-2202426650624013.mp4, approximately 69 seconds, SHA256 f0fc902a97f4bc71a378adb87f40745dacfd18ec2a375e44b5e8f5cffa7e133a.
Both measurements used the running local /extract/video endpoint after engine warm-up, the complete uploaded file, the same speech model and three OCR frames. These timings include the local upload/review response but not Facebook download, 1x playback capture, final classification, source lookup or human review.

| Stage | Before shortcut, no cache hit | Final shortcut, no cache hit |
| --- | ---: | ---: |
| Language detection | 30.936 s | 10.165 s |
| Transcription | 45.552 s | 44.380 s |
| Frame OCR | 8.546 s | 7.205 s |
| HTTP extraction/review elapsed | 85.396 s | 62.132 s |

Observed reduction on this one clip: 27.2% shorter elapsed time. Immediate repeat: 0.050 s via cache (server processing metadata 1.394 ms). Changed caption context was bound correctly on repeat. Full extraction-content hash, including transcript, frame text, segments and OCR regions, was identical before/after and on the repeat: 63940ca621222a1e10f91feceea7d8d9b5fbc9f94859ce6a963a73c86743ab59.

This is a single-case performance measurement, not a general speed guarantee. The original GMA transcript still contains the previously documented material-word errors and the speech/frame relation still requires review. Identical content proves this optimization preserved that output; it does NOT prove accurate transcription. This task did not retrain or replace ASR or the classifier.

## Checks and practical limits
- 271 backend tests passed, including cache settings/bytes invalidation, detached results, expiry, bounded entries, no caching of failed/partial extraction, engine warm-up without transcription, and language-probe counts preserving the original acceptance rule.
- Live /ready remains ready with MariaDB and Gemini primary mode. No classifier requests were made for the speed benchmark. The user-facing result layout stays on extension 1.3.43; no extension reload is needed for this backend-only update.
- CPU transcription remains the main cost for a new unique video. No GPU, smaller ASR model, reduced speech coverage or cloud/billing change was enabled.
- Browser capture fallback still records the complete video at normal speed. A cached extraction cannot remove that acquisition wait, because the server must receive and identify the file first. Direct file download is already attempted before fallback.
- Warm-up is enabled by the Gemini trial startup helper. Starting uvicorn independently uses the configured default (SURI_MEDIA_WARMUP=false) unless explicitly enabled. Text/media engines are unchanged.
- Configuration switches: SURI_VIDEO_EXTRACTION_CACHE=false disables reuse; SURI_VIDEO_EXTRACTION_CACHE_TTL_SECONDS controls TTL. To skip warm-up when using another launcher, leave SURI_MEDIA_WARMUP=false. The trial helper explicitly enables it for survey preparation.
- Prior survey gates (actual installed Chrome text/image/video test, transcript matching, questionnaire compatibility and provider quota) are not marked passed by this performance change.

## Evidence and recovery
Secret-free pre-change source backup: runtime/video-speed-backup-20261116. No database schema or data changes in this task. Original model and media assets retained.
Workspace evidence: outputs/VIDEO_SPEED_TESTS.log, outputs/video_speed_20261116 and outputs/video_speed_final_20261116. Saved review artifacts omit temporary review tokens. Final API health saved beside the benchmark.
