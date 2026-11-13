# Speech extraction improvement — 12 November 2026

## Applied configuration

The local API retains faster-whisper turbo, CPU INT8, Filipino language hint, original-language transcription, temperature zero, word timestamps and the existing speech-quality checks. It now uses low-threshold voice activity detection (threshold 0.35, minimum silence 750 ms, padding 400 ms) and previous-segment text context. Faster-whisper restores timestamps to the original audio. No caption, article, manually corrected name or generated replacement sentence is supplied to the speech decoder.

The environment examples now specify the measured turbo configuration rather than the previous tiny-model example. The active hybrid classifier and decision threshold are unchanged.

## Measured comparison

The existing fixed 16-clip FilSwitch regression sample contains 309 reference words under the same raw word-error tokenizer used for both configurations. These are read-news Taglish clips with supplied reference transcripts, not an independent test of factual classification or the user's Facebook videos.

| Configuration | Raw word errors | Reference words | Raw WER |
| --- | ---: | ---: | ---: |
| Previous turbo, no VAD, no previous-text context | 53 | 309 | 17.15% |
| Turbo, VAD and previous-text context | 50 | 309 | 16.18% |

This is a modest reduction of three word errors, not proof of uniformly accurate transcription. The first eight clips were used for decoder exploration; the remaining eight were then checked. Beam-10 decoding without VAD did not improve the aggregate of the first eight clips (17 errors in both cases). An earlier conversational interim count of 18 baseline errors for those eight clips was incorrect; the saved rows total 17.

A larger large-v3 model was also downloaded and evaluated locally. Its original-video transcription took 155.77 seconds and retained material wording errors. On its first seven completed reference clips it produced 14 raw word errors versus 13 with the existing turbo baseline. That experiment was stopped early and was not selected. No full-sample large-v3 WER is claimed. Its cached files are inactive.

## Original-video check and remaining limitation

The original 69.10-second GMA video has SHA-256 `f0fc902a97f4bc71a378adb87f40745dacfd18ec2a375e44b5e8f5cffa7e133a`. Full extraction with the selected speech-boundary settings completed in 72.17 seconds, including real frame OCR and the existing quality gates. Speech and frame text remain separate in the preview; unrelated captions are not substituted.

The new transcript improves some wording, including the later “Sa isang pahayag” segment. It still contains “Nag-high” and an unclear allegation phrase. There is no complete human-listened reference for this clip, so no numerical WER or transcript-accuracy pass is assigned to it. Questionnaire item 1.4 is not marked passed by this work. The existing explicit review step remains necessary.

## Reproduction and evidence

- `backend-api/scripts/benchmark_faster_whisper_sample.py` now accepts `--model`, `--beam-size`, `--start`, `--limit` and `--speech-boundaries`. The last flag reproduces the deployed boundary settings; omitting it reproduces the previous baseline settings.
- Private raw comparisons: `tmp/media-regression/filswitch-asr-faster-turbo.json`, `decoder-comparison-20261112.json`, `decoder-validation-20261112.json`, and `asr-large-v3-20261112.json`.
- Private complete original extraction: `tmp/media-regression/original-vad-20261112.json`.
- Backend regression suite: 125 tests passed; private log `tmp/backend-asr-20261112.log`.
- The local API was restarted. Live `/health` reported turbo with VAD and previous-text context enabled, and `/ready` returned true. A real multipart upload of the original GMA video returned HTTP 200 and an explicit review preview in 70.71 seconds. An intentionally unrelated caption was excluded. No classification was submitted. Private response: `tmp/live-asr-20261112.json`.

No classifier retraining, source override, public deployment or installed-Chrome/Facebook sign-off is implied by these ASR results.
