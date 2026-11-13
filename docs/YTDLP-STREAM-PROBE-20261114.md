# yt-dlp post-URL stream probe — 14 November 2026

The proposed `yt_dlp.YoutubeDL(...).extract_info(post_url, download=False)` path was tried against the original GMA reel `https://www.facebook.com/reel/2202426650624013` using `yt-dlp 2026.10.26` in the local `.venv`. It returned `yt_dlp.utils.DownloadError: [facebook] 2202426650624013: Cannot parse data` after approximately five seconds of command wall time. No direct media URL or audio format was returned, so ffmpeg streaming and a same-clip speed benchmark could not proceed through this route.

The active SuriPH backend has no `download_fb_video()` function: `/analyze/video` receives uploaded bytes, and `process_video()` writes a temporary media file for both audio decoding and frame OCR. The running recognizer is faster-whisper `turbo`, CPU INT8, not `base`. Replacing this flow with an audio-only URL function would remove frame OCR and would fail on the original reel in this probe. The proposed yt-dlp path was therefore **not connected to the active API or extension**. The package used for the probe was removed from `.venv`; requirements were not changed.

After the probe, local `/ready` still returned HTTP 200, MariaDB `available`, and model `ready`. Extension 1.3.37 retains its earlier direct media URL attempt and full-capture fallback. No new speed or transcription accuracy claim is made from this failed probe.
