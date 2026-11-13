"""Compare runtime ASR candidates on a fixed, separate Taglish test sample.

The manifest is selected before decoding. Dataset transcripts are references,
not a listening review of SuriPH's Facebook videos.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from compare_video_transcripts import load_audio, word_error_rate  # noqa: E402
from src.media_processing import _prepare_whisper_import  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("sample_dir", type=Path)
    parser.add_argument("--models", nargs="+", default=["tiny", "turbo"])
    parser.add_argument("--language", help="Optional controlled speech-language hint")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    items = json.loads((args.sample_dir / "manifest.json").read_text(encoding="utf-8-sig"))
    audio = [(item, load_audio(args.sample_dir / item["file_name"])) for item in items]
    _prepare_whisper_import()
    import whisper

    report = {"sample_rule": "Every 53rd row of the published FilSwitch test metadata in UUID order, starting at row 0",
              "reference_source": "FilSwitch test/metadata.csv, manually validated read speech (per dataset card)",
              "language_hint": args.language,
              "models": {}}
    for name in args.models:
        load_start = time.perf_counter()
        model = whisper.load_model(name, download_root=str(ROOT / "data" / "runtime-models" / "whisper"))
        model_report = {"load_seconds": round(time.perf_counter() - load_start, 2), "clips": []}
        for index, (item, samples) in enumerate(audio, 1):
            started = time.perf_counter()
            raw = model.transcribe(
                samples, fp16=False, task="transcribe", language=args.language,
                condition_on_previous_text=False,
                temperature=0.0, word_timestamps=True, hallucination_silence_threshold=2.0,
            )
            elapsed = time.perf_counter() - started
            error = word_error_rate(item["text"], raw.get("text", ""))
            row = {"uuid": item["uuid"], "audio_seconds": round(len(samples) / 16000, 2),
                   "processing_seconds": round(elapsed, 2), "language": raw.get("language"),
                   "reference": item["text"], "transcript": raw.get("text", ""), **error}
            model_report["clips"].append(row)
            report["models"][name] = model_report
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"model": name, "clip": index, "wer": error["wer"],
                              "processing_seconds": row["processing_seconds"]}), flush=True)
        total_words = sum(row["reference_words"] for row in model_report["clips"])
        total_errors = sum(row["word_errors"] for row in model_report["clips"])
        model_report["aggregate"] = {"reference_words": total_words, "word_errors": total_errors,
                                     "wer": round(total_errors / total_words, 4),
                                     "processing_seconds": round(sum(row["processing_seconds"] for row in model_report["clips"]), 2)}
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"model": name, "aggregate": model_report["aggregate"]}), flush=True)


if __name__ == "__main__":
    main()
