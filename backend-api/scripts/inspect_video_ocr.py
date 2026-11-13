"""Save time-stamped EasyOCR detections from one video for manual region review."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.media_processing import _get_ocr_reader, ffmpeg_executable  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("--seconds", type=float, nargs="+", default=[1, 23, 46, 65])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    import cv2

    report = {"video": str(args.video), "frames": []}
    with tempfile.TemporaryDirectory() as folder:
        for second in args.seconds:
            frame = Path(folder) / f"frame-{second:g}.png"
            run = subprocess.run(
                [ffmpeg_executable(), "-hide_banner", "-loglevel", "error", "-y", "-ss", str(second),
                 "-i", str(args.video), "-frames:v", "1", str(frame)], capture_output=True, text=True,
                timeout=60,
            )
            if run.returncode or not frame.is_file():
                raise RuntimeError(f"Could not sample frame at {second} seconds")
            image = cv2.imread(str(frame))
            height, width = image.shape[:2]
            detections = []
            for box, text, confidence in _get_ocr_reader().readtext(image, detail=1, paragraph=False):
                detections.append({"text": str(text), "confidence": float(confidence),
                                   "box": [[round(float(x), 1), round(float(y), 1)] for x, y in box],
                                   "normalized_center": [round(sum(point[0] for point in box) / 4 / width, 3),
                                                         round(sum(point[1] for point in box) / 4 / height, 3)]})
            report["frames"].append({"time_seconds": second, "width": width, "height": height,
                                     "detections": detections})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"sample_times": args.seconds, "counts": [len(x["detections"]) for x in report["frames"]]}))


if __name__ == "__main__":
    main()
