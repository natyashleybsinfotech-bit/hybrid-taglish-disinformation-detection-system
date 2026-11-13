# Filipino news reel transcription audit — 2026-11-02

> Historical pre-change audit. Current multi-video results and the mandatory video review flow are in [VIDEO-EXTRACTION-VALIDATION-20261103.md](VIDEO-EXTRACTION-VALIDATION-20261103.md).

## Exact case and status

- Original: https://www.facebook.com/reel/2202426650624013
- Downloaded Facebook format: `sd` MP4; 69.10 s; H.264 video plus stereo AAC audio.
- Local regression file: `tmp/media-regression/facebook-2202426650624013.mp4` (private, untracked).
- SHA-256: `F0FC902A97F4BC71A378ADB87F40745DACFD18EC2A375E44B5E8F5CFFA7E133A`.
- Running backend `/health` reported Whisper `tiny`. Its language is auto-detected; `task="transcribe"` preserves the original language. The hybrid classifier was not changed.
- The current full `tiny` pipeline rejects this clip at its speech-quality gate. A separate `medium` full-pipeline run also rejects it. Neither should produce a prediction from this clip.

## Raw diagnostic comparison on the same downloaded audio

These are **unverified raw ASR outputs**, not a listening-checked transcript or accepted replacement. The final comparison used the API's Python environment and `temperature=0.0` for both models; it excludes model load time.

| Multilingual Whisper model | Detected language | ASR processing time, excluding model load | Material raw-output errors observed |
| --- | --- | ---: | --- |
| `tiny` (running setting) | `tl` | 12.44 s | “live bill,” distorted Gracioso and Matibag, corrupted qualifiers/sentences |
| `medium` (candidate only) | `tl` | 108.16 s | “libel at cyber libel” and Matibag improved; Gracioso and parts of the allegation/response still distorted |

An exploratory comparison with default Whisper temperature fallback also tried `base` (15.21 s) and `small` (42.99 s); both still had material word errors, and those timings are not directly comparable with the deterministic final table. The exact final raw strings and segment times remain in the private local file `tmp/media-regression/asr-deterministic-final.json`. There is **no verified after transcript** yet. A person must listen to the original 69-second clip and check a reference before word error rate and material-error counts can be reported. The comparison script supports that reference through `--reference`; model confidence alone is not treated as correctness.

The installed Whisper default uses a temperature fallback sequence `(0.0, 0.2, 0.4, 0.6, 0.8, 1.0)`. Repeated runs on this reel differed and one passed the old extraction gate. Runtime decoding is now fixed at `temperature=0.0`; two consecutive exact-reel runs in the API environment both failed closed (16.12 s and 10.90 s). The restarted API returned HTTP 422 for the original reel in 15.63 s. A second separate Filipino clip that had once produced a garbled accepted extraction also returned HTTP 422 from the restarted API in 19.35 s.

The deterministic `medium` output also has no segment from 45.7 to 56.2 seconds in the middle of the report. A generic substantial-middle-gap check was added; this is another rejection condition, not a transcript repair. After loading that final guard, the localhost API again returned HTTP 422 for the exact reel (23.02 s) and remained ready with MariaDB and the unchanged hybrid classifier.

## Capture check

The downloaded original was replayed in an isolated Chrome page through `captureStream()` and `MediaRecorder`, using the same browser APIs as the extension's fallback. The captured WebM has one audio track. Decoded original audio: 69.100 s; captured audio: 69.120 s; alignment offset: 0.006 s; overlap: 69.100 s; waveform correlation: 0.9995. This supports complete, same-source audio in the **isolated replay**. It does not prove that the already-observed Facebook in-page capture took the same path; no original saved capture from that result exists.

A second isolated replay started with the selected video positioned about 20 seconds in, rewound it, and then captured it. Its decoded audio was 69.120 s, aligned at -0.013 s, overlapped 69.087 s, and again correlated 0.9995 with the original. This checks the mid-playback rewind path without claiming access to the earlier failed Facebook capture.

The extension capture now seeks to the start, starts recording before playback, and errors if no audio track is capturable. It never substitutes a caption on that failure.

## OCR audit on the same reel

Raw EasyOCR detections were saved with boxes and timestamps in `tmp/media-regression/ocr-regions.json`. The 1, 23, 46, and 65-second frames had 11, 9, 10, and 7 raw detections. The region filter retained three story lower-third lines at each of 23 and 46 seconds, including the libel/cyberlibel headline and named parties. It excluded all 11 intro-frame detections, 6 at 23 seconds, 7 at 46 seconds, and all 7 end-card detections. Excluded material included channel marks, 24 Oras logo, the clock, unrelated scrolling weather/entertainment text, and the end-card call to action. The retained OCR still reads `AI CYBERLIBEL` where the graphic appears to say `AT CYBERLIBEL`; this is an unresolved OCR word error and must not be silently rewritten.

Frame OCR now retains bounding boxes and sample times. The result UI separates speech from on-screen text and offers frame timestamps. The filter is geometric and heuristic; it does not prove a frame line is claim-relevant across other videos.

## Separate Filipino coverage checks

Two other public GMA News clips were downloaded privately: `xbssb52` (70.72 s, ICC status conference) and `xbss9ly` (61.51 s, motorcycle accident). Both contain AAC audio. The current `tiny` gate rejected the motorcycle clip after 11.38 s. The first ICC extraction run was accepted after 28.28 s even though its transcript contained garbled words; a second run rejected it at the speech gate after 28.82 s. This demonstrates that segment diagnostics alone are insufficient and can be unstable near the boundary. The saved accepted ICC extraction fails the new speech/story-frame agreement check. This check rejects obvious mismatch; agreement is not proof of word correctness. No classifier was invoked for these coverage checks. Neither clip has a listening-checked reference or WER yet.

## Regression and release gate

- The original media stays local and untracked; the URL and hash identify the regression case without adding copyrighted video to the repository.
- `backend-api/scripts/compare_video_transcripts.py` compares multilingual models on the same file and can calculate WER from a listening-checked reference.
- `backend-api/scripts/inspect_video_ocr.py` preserves raw OCR boxes/timestamps for audit.
- `backend-api/scripts/compare_capture_audio.py` checks captured audio alignment against the original.
- Media and API tests passed (52 after deterministic decoding and consistency checks; 18 focused media tests after the final gap check), and the extension build passed. These checks do not establish transcription accuracy.
- **Open:** obtain a listening-checked transcript for this clip; measure word and material errors for each candidate; test additional separate Filipino/Taglish clips; then choose any new ASR model. Until then, keep `tiny` and fail closed on this reel.
- Additional clips have been exercised for acquisition and gating, but still need listening-checked references before they count as transcription accuracy tests.
- A private listening worksheet with the candidate text and missing interval is at `tmp/media-regression/listening-review.md`. It requires a human to fill the words heard from the original audio before WER/material-error counts can be calculated.
