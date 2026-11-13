# Video acquisition speed check — 14 November 2026

## Change on extension 1.3.37

For a selected Facebook video with an HTTPS Facebook/fbcdn media URL, the MV3 background worker now tries to download that exact media file and upload it to the existing `/analyze/video` endpoint. This can remove the full-duration, real-time browser recording step. If the URL is expired, blocked, returns HTTP 206 (only part of the video), or contains no decodable audio track, the extension falls back to the existing complete, normal-speed recording. `blob:` media goes directly to recording. Other backend extraction failures are shown as errors and are not silently retried with another input. The selected post, caption, and video are checked again before displaying a result. No model, classification threshold, or evidence rule changed.

The modal now identifies whether it is downloading, recording, or transcribing and shows elapsed time. The fallback retains the existing audio and incomplete-input safeguards. Downloaded media is limited to 50 MiB; oversized videos still produce an error.

## What was measured

Earlier local backend replays of the saved 69-second GMA clip took roughly 81–110 seconds for extraction, depending on the run. A separate 62-second eGov clip took 165.848 seconds in one local extraction. These are **backend processing times**, not current end-to-end Facebook timings. A real-time capture can add approximately the clip duration before backend work begins. The new direct path removes that capture step **only when the selected media URL yields the complete playable video with audio**. No signed-in Facebook before/after timing was obtained for extension 1.3.37, so an actual speed improvement has not yet been measured.

The original GMA transcript still contains material speech errors. Questionnaire item 1.4 remains **Failed**; a faster acquisition path does not establish transcription correctness.

## Checks on this build

- Extension build passed.
- 26 extension behavior tests passed, including direct upload, expired URL fallback, HTTP 206 fallback, video-only stream fallback, and backend-error handling.
- Product and video review contracts passed.
- Isolated Edge HTTPS Facebook fixture loaded the built extension, observed a direct fetch attempt only for the selected post's video, and observed fallback without a fabricated prediction when that fixture URL was unavailable. This fixture did not access the user's signed-in account or prove a successful direct download from a live Facebook post.
- Local `/ready` returned HTTP 200 with MariaDB available and the pinned hybrid model ready.

## Remaining verification

Reload `chrome-extension/dist` in `chrome://extensions`, refresh Facebook, and time a real selected video from clicking Analyze until the result or extraction error. Record whether the modal says **Downloading** or **Recording** and whether the audio is complete. CPU speech recognition and OCR remain a substantial part of the wait even after a successful direct download. If Facebook exposes only a segmented or protected media URL, the fallback still takes at least the full video duration.
