"""Freeze synthetic image/video renditions of four already selected text claims.

These exercise acquisition modes. They are paired observations, not four new
independent claims or examples of natural Facebook media.
"""

import csv
import hashlib
import json
import subprocess
import sys
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend-api"))
from src.media_processing import ffmpeg_executable

FOLDER = ROOT / "research-data/evaluation-20261029"
MANIFEST = ROOT / "docs/research/EVALUATION-BATCH-MANIFEST.json"


def main():
    media_csv = FOLDER / "media_review_batch.csv"
    repair = sys.argv[1:] == ["--repair-video-audio"]
    if media_csv.exists() and not repair:
        raise SystemExit("Frozen media supplement already exists; refusing to replace it")
    if repair and not media_csv.exists():
        raise SystemExit("No media supplement exists to repair")
    previous = {}
    if repair:
        with media_csv.open(encoding="utf-8-sig", newline="") as stream:
            previous = {row["case_id"]: row for row in csv.DictReader(stream)}
    with (FOLDER / "review_batch.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = {row["case_id"]: row for row in csv.DictReader(stream)}
    assignments = [("M001", "image", "S001"), ("M002", "image", "S013"), ("M003", "video", "S002"), ("M004", "video", "S014")]
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 31)
    outputs = []
    for case_id, mode, source_id in assignments:
        source = rows[source_id]
        image = Image.new("RGB", (1400, 840), "white")
        draw = ImageDraw.Draw(image)
        words = source["text"].split()
        lines, current = [], ""
        for word in words:
            trial = (current + " " + word).strip()
            if draw.textlength(trial, font=font) > 1280 and current:
                lines.append(current)
                current = word
            else:
                current = trial
        if current:
            lines.append(current)
        if len(lines) > 20:
            raise ValueError(f"Text will not fit visibly in {case_id}")
        draw.multiline_text((60, 65), "\n".join(lines), font=font, fill="black", spacing=9)
        output = FOLDER / f"{case_id}.{'png' if mode == 'image' else 'mp4'}"
        if mode == "image" and not repair:
            image.save(output)
        elif mode == "video":
            still = FOLDER / f"{case_id}-frame.png"
            silence = FOLDER / f"{case_id}-silence.wav"
            image.save(still)
            with wave.open(str(silence), "wb") as stream:
                stream.setnchannels(1)
                stream.setsampwidth(2)
                stream.setframerate(16000)
                stream.writeframes(b"\x00\x00" * 16000 * 3)
            subprocess.run([ffmpeg_executable(), "-loglevel", "error", "-y", "-loop", "1", "-i", str(still), "-i", str(silence), "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(output)], check=True, timeout=90)
            still.unlink()
            silence.unlink()
        outputs.append({"case_id": case_id, "mode": mode, "paired_text_case": source_id, "record_id": source["record_id"], "media_file": output.name, "sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "human_label": previous.get(case_id, {}).get("human_label", ""), "evidence_url": previous.get(case_id, {}).get("evidence_url", ""), "review_status": previous.get(case_id, {}).get("review_status", "pending_human_review"), "extraction_review": previous.get(case_id, {}).get("extraction_review", "")})
    with media_csv.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=outputs[0].keys())
        writer.writeheader()
        writer.writerows(outputs)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if repair:
        manifest.setdefault("amendments", []).append({"reason": "First video fixtures had no audio stream and the supported video route returned HTTP 422; silent audio track added before human review", "previous_video_sha256": {case_id: previous[case_id]["sha256"] for case_id in ("M003", "M004")}})
    manifest["media_cases"] = len(outputs)
    manifest["media_supplement"] = [{key: row[key] for key in ("case_id", "mode", "paired_text_case", "record_id", "sha256")} for row in outputs]
    manifest["media_note"] = "Synthetic renderings of four selected text claims; dependent paired observations, not four independent accuracy cases or natural Facebook media"
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"media_cases": 4, "image": 2, "video": 2, "paired_text_cases": [item["paired_text_case"] for item in outputs]}))


if __name__ == "__main__":
    main()
