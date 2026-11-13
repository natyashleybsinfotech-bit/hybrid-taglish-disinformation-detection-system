"""Inspect speech/frame agreement from saved private ASR and OCR diagnostics."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.media_processing import _speech_frame_consistent, _story_frame_detections

COMMON = {"ang", "at", "mga", "ng", "na", "sa", "si", "sina", "ni", "the", "and", "for", "of", "to", "rep"}


def terms(value: str, *, include_compounds: bool = False) -> set[str]:
    words = re.findall(r"[^\W_]+", value.casefold())
    result = {word for word in words if len(word) >= 3 and word not in COMMON}
    if include_compounds:
        result.update(words[index] + words[index + 1] for index in range(len(words) - 1)
                      if len(words[index]) >= 3 and len(words[index + 1]) >= 3
                      and words[index] not in COMMON and words[index + 1] not in COMMON)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asr", type=Path, required=True)
    parser.add_argument("--ocr", type=Path, required=True)
    args = parser.parse_args()
    transcript = json.loads(args.asr.read_text(encoding="utf-8"))["text"]
    ocr = json.loads(args.ocr.read_text(encoding="utf-8"))
    lines = []
    rows = []
    for frame in ocr["frames"]:
        detections = [(item["box"], item["text"], item["confidence"]) for item in frame["detections"]]
        kept, rejected = _story_frame_detections(
            detections, frame["width"], frame["height"], frame["time_seconds"]
        )
        rows.append({"seconds": frame["time_seconds"], "retained": [item["text"] for item in kept], "rejected": rejected})
        lines.extend(item["text"] for item in kept)
    visible = terms(" ".join(lines))
    shared = visible & terms(transcript, include_compounds=True)
    print(json.dumps({
        "frames": rows,
        "visible_terms": sorted(visible),
        "shared_terms": sorted(shared),
        "speech_frame_overlap": len(shared) / len(visible) if visible else None,
        "gate_passes": _speech_frame_consistent([transcript], lines),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
