"""Real cached-fixture speech/OCR checks; not natural Filipino/Taglish accuracy."""
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend-api"), str(ROOT / "backend-api/src")]
from media_processing import process_video, ffmpeg_executable


def word_error_rate(reference, actual):
    expected = re.findall(r"\w+", reference.casefold())
    received = re.findall(r"\w+", actual.casefold())
    previous = list(range(len(received) + 1))
    for i, word in enumerate(expected, 1):
        current = [i]
        for j, other in enumerate(received, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (word != other)))
        previous = current
    return previous[-1] / len(expected) if expected else None


def main():
    folder = ROOT / "tmp" / "verification-20261102-media"
    folder.mkdir(parents=True, exist_ok=True)
    sample = ROOT / "tmp" / "media-check" / "sample.mp4"
    image = ROOT / "tmp" / "media-check" / "sample.png"
    if not sample.is_file() or not image.is_file():
        raise SystemExit("Run verify_media_local.py first to generate the declared synthetic fixtures.")
    report = {"synthetic_fixtures": True, "natural_taglish_accuracy_established": False,
              "reference": "Read the full article before sharing. Check the original source."}
    spoken = process_video(sample.read_bytes())
    report["spoken_video"] = {
        "transcript": spoken["transcript_text"], "frame_text": spoken["frame_ocr_text"],
        "word_error_rate": word_error_rate(report["reference"], spoken["transcript_text"]),
        "transcript_segments": spoken["transcript_segments"],
        "sampled_frames": spoken["sampled_frames"],
    }
    silent_path = folder / "silent.mp4"
    subprocess.run([ffmpeg_executable(), "-hide_banner", "-loglevel", "error", "-y",
                    "-loop", "1", "-i", str(image), "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
                    "-t", "3", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(silent_path)],
                   check=True, capture_output=True, timeout=45)
    silent = process_video(silent_path.read_bytes())
    report["silent_video"] = {"transcript": silent["transcript_text"], "status": silent["transcript_status"],
                              "frame_text": silent["frame_ocr_text"], "no_invented_speech": not silent["transcript_text"]}
    report["passed"] = (report["spoken_video"]["word_error_rate"] == 0.0
                        and report["silent_video"]["no_invented_speech"]
                        and "article" in silent["frame_ocr_text"].casefold())
    (ROOT / "docs" / "MEDIA-QUALITY-20261102.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
