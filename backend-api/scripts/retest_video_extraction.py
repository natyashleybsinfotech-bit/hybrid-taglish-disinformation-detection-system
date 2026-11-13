"""Retest one supplied video through the current extraction code, without classifying."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.media_processing import MediaProcessingError, process_video


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    blob = args.video.read_bytes()
    started = time.perf_counter()
    try:
        extraction = process_video(blob, args.video.suffix)
        report = {"status": "completed", "sha256": hashlib.sha256(blob).hexdigest(),
                  "processing_seconds": round(time.perf_counter() - started, 3),
                  "extraction": extraction}
    except MediaProcessingError as exc:
        report = {"status": "failed", "sha256": hashlib.sha256(blob).hexdigest(),
                  "processing_seconds": round(time.perf_counter() - started, 3),
                  "error": str(exc)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "sha256": report["sha256"],
                      "processing_seconds": report["processing_seconds"],
                      "transcript_characters": len(report.get("extraction", {}).get("transcript_text", "")),
                      "frame_text_characters": len(report.get("extraction", {}).get("frame_ocr_text", "")),
                      "error": report.get("error")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
