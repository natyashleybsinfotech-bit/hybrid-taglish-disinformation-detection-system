"""Evaluate CPU CTranslate2 Whisper on the same fixed FilSwitch sample."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from compare_video_transcripts import load_audio, word_error_rate  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("sample_dir", type=Path)
    parser.add_argument("--dependency-dir", type=Path)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="turbo")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--speech-boundaries", action="store_true", help="Use the deployed VAD and previous-text context settings")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.dependency_dir:
        sys.path.insert(0, str(args.dependency_dir.resolve()))
    from faster_whisper import WhisperModel

    items = json.loads((args.sample_dir / "manifest.json").read_text(encoding="utf-8-sig"))
    started = time.perf_counter()
    model = WhisperModel(args.model, device="cpu", compute_type="int8", download_root=str(args.model_root))
    report = {"implementation": "faster-whisper CTranslate2 INT8 CPU", "model": args.model,
              "beam_size": args.beam_size,
              "speech_boundaries": args.speech_boundaries,
              "language_hint": "tl", "load_seconds": round(time.perf_counter() - started, 2),
              "sample_rule": "Every 53rd FilSwitch test metadata row in UUID order, starting at 0",
              "clips": []}
    chosen = items[args.start:][:args.limit] if args.limit is not None else items[args.start:]
    report["sample_start"] = args.start
    report["sample_count"] = len(chosen)
    for index, item in enumerate(chosen, 1):
        audio = load_audio(args.sample_dir / item["file_name"])
        started = time.perf_counter()
        boundary_options = ({"vad_parameters": {
            "threshold": .35, "min_silence_duration_ms": 750, "speech_pad_ms": 400,
        }} if args.speech_boundaries else {})
        segments, info = model.transcribe(
            audio, language="tl", task="transcribe", temperature=0.0,
            condition_on_previous_text=args.speech_boundaries, word_timestamps=True, vad_filter=args.speech_boundaries,
            beam_size=args.beam_size,
            **boundary_options,
        )
        rows = list(segments)
        elapsed = time.perf_counter() - started
        transcript = " ".join(segment.text.strip() for segment in rows).strip()
        errors = word_error_rate(item["text"], transcript)
        report["clips"].append({"uuid": item["uuid"], "audio_seconds": round(len(audio) / 16000, 2),
                                "processing_seconds": round(elapsed, 2), "language": info.language,
                                "reference": item["text"], "transcript": transcript, **errors})
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"clip": index, "wer": errors["wer"],
                          "processing_seconds": round(elapsed, 2)}), flush=True)
    words = sum(row["reference_words"] for row in report["clips"])
    errors = sum(row["word_errors"] for row in report["clips"])
    report["aggregate"] = {"reference_words": words, "word_errors": errors,
                           "raw_wer": round(errors / words, 4),
                           "processing_seconds": round(sum(row["processing_seconds"] for row in report["clips"]), 2)}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"aggregate": report["aggregate"]}), flush=True)


if __name__ == "__main__":
    main()
