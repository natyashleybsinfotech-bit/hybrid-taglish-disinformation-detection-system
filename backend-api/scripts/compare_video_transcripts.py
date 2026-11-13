"""Diagnostic ASR comparison on one original clip; never sends text to classifier."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.media_processing import _prepare_whisper_import, ffmpeg_executable  # noqa: E402


def load_audio(path: Path):
    import numpy as np

    with tempfile.TemporaryDirectory() as folder:
        wav = Path(folder) / "source.wav"
        run = subprocess.run(
            [ffmpeg_executable(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(path),
             "-vn", "-ac", "1", "-ar", "16000", str(wav)], capture_output=True, text=True,
            timeout=240,
        )
        if run.returncode or not wav.is_file():
            raise RuntimeError("Could not decode the original clip's audio")
        with wave.open(str(wav), "rb") as source:
            if source.getframerate() != 16000 or source.getnchannels() != 1:
                raise RuntimeError("Unexpected decoded audio format")
            return np.frombuffer(source.readframes(source.getnframes()), dtype="<i2").astype(np.float32) / 32768.0


def word_error_rate(reference: str, hypothesis: str) -> dict:
    def words(value: str) -> list[str]:
        return re.findall(r"[^\W_]+(?:[-'][^\W_]+)*", value.casefold(), flags=re.UNICODE)

    expected, actual = words(reference), words(hypothesis)
    if not expected:
        raise ValueError("The listening-checked reference is empty")
    previous = list(range(len(actual) + 1))
    for row, word in enumerate(expected, 1):
        current = [row]
        for column, candidate in enumerate(actual, 1):
            current.append(min(previous[column] + 1, current[column - 1] + 1,
                               previous[column - 1] + int(word != candidate)))
        previous = current
    return {"reference_words": len(expected), "word_errors": previous[-1],
            "wer": round(previous[-1] / len(expected), 4)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("--models", nargs="+", default=["tiny", "base"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference", type=Path, help="Transcript checked by listening to this exact clip")
    parser.add_argument("--language", help="Optional speech language hint for a controlled diagnostic; default auto-detect")
    args = parser.parse_args()
    audio = load_audio(args.video)
    _prepare_whisper_import()
    import whisper

    report = {"video": str(args.video), "audio_seconds": len(audio) / 16000, "results": {}}
    for name in args.models:
        started = time.perf_counter()
        model = whisper.load_model(name, download_root=str(ROOT / "data" / "runtime-models" / "whisper"))
        load_seconds = time.perf_counter() - started
        started = time.perf_counter()
        raw = model.transcribe(
            audio, fp16=False, task="transcribe", language=args.language,
            condition_on_previous_text=False,
            temperature=0.0,
            word_timestamps=True, hallucination_silence_threshold=2.0,
        )
        processing_seconds = time.perf_counter() - started
        report["results"][name] = {
            "language": raw.get("language"), "language_hint": args.language,
            "load_seconds": load_seconds,
            "processing_seconds": processing_seconds, "text": raw.get("text", ""),
            "segments": [{"start": x.get("start"), "end": x.get("end"), "text": x.get("text"),
                          "avg_logprob": x.get("avg_logprob"), "no_speech_prob": x.get("no_speech_prob")}
                         for x in raw.get("segments", [])],
        }
        if args.reference:
            report["results"][name]["word_error"] = word_error_rate(
                args.reference.read_text(encoding="utf-8"), raw.get("text", ""))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"model": name, "language": raw.get("language"),
                          "processing_seconds": round(processing_seconds, 2),
                          "text": raw.get("text", "")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
