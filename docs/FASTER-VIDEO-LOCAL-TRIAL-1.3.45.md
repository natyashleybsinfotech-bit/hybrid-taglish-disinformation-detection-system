# Faster video local trial — SuriPH 1.3.45, 16 November 2026

> Historical record: the later 20 November local-model migration supersedes any active Gemini/cloud-provider description and cloud timings below. See [current source](CURRENT-SOURCE-20261120.md) and [removal record](GEMINI-REMOVAL-20261120.md). Older results remain preserved as historical evidence.

## Active changes
The user approved trying Google Gemini audio transcription, and later explicitly approved sending up to 17 existing FilSwitch reference audio clips for a comparison. The actual frozen sample contains 16 audio clips (309 raw reference words), the same existing selection used by the prior local-ASR benchmark. Reference answers stayed local and were not included in the provider request. The first broader-dataset egress attempt was rejected by automatic approval review; it was retried only after the user's specific approval, not through a workaround.

SURI_SPEECH_PROVIDER=gemini is now enabled only in the private local settings. The original local Whisper implementation and its saved model assets remain available; no retraining, deletion, new billing activation, quota increase, public deployment or hidden transcription substitution was performed.

The whole uploaded video audio is decoded to 16kHz mono WAV, divided into consecutive server-owned ten-second parts, and all parts are sent in ONE bounded Gemini request. The provider must return every chunk ID exactly once; malformed/missing/duplicate chunks, failed requests and truncated responses are rejected. Text is requested verbatim in the original spoken languages, with uncertainty marked rather than guessed. Chunk timestamps come from the server's actual audio boundaries, not invented word timestamps. They are coarse part ranges, not precise word alignment.

The existing sampled-frame OCR still runs. The cached extraction contains actual speech and frame text. External-audio results require the existing review step before classification, including through the analyze/video endpoint. This is automatic ASR requiring comparison with the source, not a guarantee that every word is correct.

Warm-up prepares OCR only in external-audio mode; the large local Whisper model is not loaded or called. Switching back to local mode restores the normal local warm-up and decoder path.

## Measured result: complete original video, not a caption
The same approximately 69-second GMA regression video was submitted to the running /extract/video endpoint with NO caption. Input SHA256: f0fc902a97f4bc71a378adb87f40745dacfd18ec2a375e44b5e8f5cffa7e133a.

| Measurement | Local speech path (previous final test) | External-audio local trial |
| --- | ---: | ---: |
| Complete extraction/review HTTP elapsed | 62.132 s | 10.577 s |
| Speech processing | 44.380 s, plus 10.165 s detection | 5.739 s |
| Frame OCR | 7.205 s | 4.470 s |
| Immediate repeated extraction | 0.050 s | 0.025 s |

These are single-case local measurements. The 10.6 s result includes local upload, full audio transcription and three OCR frames, but excludes Facebook download, normal-speed playback capture, the human review, source checking and final classification. The system does not wait an artificial ten seconds or promise that every clip finishes in that time. A failed direct URL still needs complete real-time capture; that acquisition wait cannot be removed by a faster ASR backend.

## Quality comparison and rejected first approach
The first full-audio single-part probe took about 3 seconds but omitted the Matibag quotation. That approach was not activated. Requiring server-owned short audio parts restored the omitted passage in the chunked probe. Material name/word errors remain in the news transcript; there is no complete listening-checked GMA reference, so no news-clip accuracy or WER is claimed.

On the SAME frozen 16-clip reference set, the same dataset number-aware WER evaluator gave:
- Saved local Whisper hypotheses: 13.44% normalized WER.
- Gemini batch hypotheses: 14.10% normalized WER.

Lower is better: the new sample score is slightly worse, not an accuracy improvement. This small, previously used reference set and a batched provider request do not establish real-world Facebook accuracy or a universal latency advantage. The batch request took 16.192 s; it is not comparable to single-clip streaming latency. Review remains necessary, including for names, quantities, negation and allegations.

## Caption fallback and failure behavior
If actual speech quality is rejected and there is a complete nonempty caption, the server can analyze only that caption. The result is explicitly bound as caption_fallback and Content checked says Video caption only. It contains no fabricated transcript or frame text. Missing, collapsed, ellipsis-ended and bare WATCH/LOOK captions are rejected for fallback. Upload/type/size/FFmpeg errors and provider outages are not silently converted to caption predictions. Provider unavailability returns 503; busy/quota returns 429.

The local Whisper path now checks the existing speech quality gate as segments arrive and stops later chunks once an already-rejected segment makes a clean result impossible. With a usable caption, it avoids the optional second English-detection transcription retry. Without a usable caption, original retry behavior remains. It does not accept the partial transcript as complete. For external speech, an unclear response also permits the explicitly labelled caption fallback; a service error does not.

Direct video download now allows eight seconds for the initial HTTP response. Once headers arrive, the existing thirty-second full-download allowance begins. It still validates complete ranges and fails rather than uploading a partial video. Capture remains normal speed with full-clip completion checks.

## Verification
- 281 backend tests passed: chunk completeness, owned timestamps, no fabricated transcript on service failure, no local Whisper in external mode, stream fail-fast behavior, caption-only input binding and non-fallback technical failures.
- 40 extension behavior tests passed; production build succeeded at 1.3.45.
- Final isolated Facebook-origin modal rehearsal passed: caption/media chooser scoping, label/score display, post switching, source-only refresh, bilingual switching and stale reload handling. This is isolated Edge, not a current signed-in Chrome/Facebook observation.
- Live no-caption video benchmark returned review_required with real audio-derived text, three sampled frames and external_audio / server_audio_chunks metadata. Immediate repeat content hash matched the first extraction, showing cache reuse. /ready stayed true with MariaDB and the primary classifier available.
- No database schema changes in this task; current schema remains 8. No final prediction was requested for the performance benchmark.

## Use and rollback
Reload SuriPH 1.3.45 in chrome://extensions and refresh Facebook, then make a new video check. The updated API is already running. Use scripts/start-survey-local.ps1 for later starts; it reads the current manifest version and avoids duplicate API startup.

To roll back ONLY speech processing: set SURI_SPEECH_PROVIDER=local in backend-api/.env.local and restart this project's API. Existing classifier settings and video text review are unchanged. Disable caption fallback by restoring the backed-up endpoint changes if desired; secret-free pre-change source backup: runtime/video-failfast-backup-20261116. Do not reset MariaDB to roll back audio/UI code.

Privacy details now disclose that actual video audio is sent to Google Gemini when external transcription is enabled. The result window retains SuriPH branding. API keys remain backend-only. Default limits remain one provider request at a time, four/minute and 100/day; audio plus final classification generally uses two requests before caching. No quota or billing upgrade was enabled.

This reversible local trial improves observed speed, with a documented accuracy tradeoff and unresolved actual-Chrome survey gates. It is not a full survey/deployment sign-off. Official audio API documentation: https://ai.google.dev/gemini-api/docs/audio .

## Artifacts
Workspace outputs: GEMINI_AUDIO_TESTS.log, VIDEO_FAILFAST_TESTS.log, gemini_audio_trial_20261116 (first rejected approach, chunked probe, frozen reference comparison), gemini_audio_video_20261116 (no-caption HTTP benchmark and health).
