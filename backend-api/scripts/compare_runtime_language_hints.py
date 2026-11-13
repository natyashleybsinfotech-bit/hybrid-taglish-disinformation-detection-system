"""Compare the active ASR model's Filipino hint with auto detection on one clip.

Diagnostic only: neither hypothesis is sent to the classifier or used as truth.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from scripts.compare_video_transcripts import load_audio  # noqa: E402
from src.media_processing import _get_whisper_model  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audio = load_audio(args.video)
    model = _get_whisper_model()
    report = {
        "sha256": hashlib.sha256(args.video.read_bytes()).hexdigest(),
        "audio_seconds": round(len(audio) / 16000, 3),
        "engine": config.WHISPER_ENGINE,
        "model": config.WHISPER_MODEL_NAME,
        "results": {},
    }
    for name, language in (("filipino_hint", "tl"), ("auto_detect", None)):
        started = time.perf_counter()
        raw = model.transcribe(
            audio, fp16=False, task="transcribe", language=language,
            condition_on_previous_text=config.WHISPER_ENGINE == "faster-whisper", temperature=0.0,
            word_timestamps=True, hallucination_silence_threshold=2.0,
            no_speech_threshold=config.TRANSCRIPT_MAX_NO_SPEECH_PROB,
            logprob_threshold=config.TRANSCRIPT_MIN_AVG_LOGPROB,
            compression_ratio_threshold=config.TRANSCRIPT_MAX_COMPRESSION_RATIO,
        )
        report["results"][name] = {
            "language": raw.get("language"),
            "processing_seconds": round(time.perf_counter() - started, 3),
            "text": raw.get("text", ""),
            "segments": raw.get("segments", []),
        }
        print(json.dumps({"setting": name, "detected_language": raw.get("language"),
                          "seconds": report["results"][name]["processing_seconds"],
                          "characters": len(raw.get("text", ""))}), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
