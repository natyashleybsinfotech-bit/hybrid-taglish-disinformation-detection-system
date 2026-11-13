"""Compare a browser capture with its original decoded audio, without ASR."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.media_processing import ffmpeg_executable  # noqa: E402


def decode(path: Path):
    import numpy as np

    result = subprocess.run(
        [ffmpeg_executable(), "-hide_banner", "-loglevel", "error", "-i", str(path),
         "-vn", "-ac", "1", "-ar", "8000", "-f", "f32le", "pipe:1"],
        capture_output=True, timeout=240,
    )
    if result.returncode or not result.stdout:
        raise RuntimeError(f"Cannot decode audio from {path}")
    return np.frombuffer(result.stdout, dtype="<f4").copy()


def main():
    from scipy.signal import correlate, correlation_lags
    import numpy as np

    parser = argparse.ArgumentParser()
    parser.add_argument("original", type=Path)
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    original, capture = decode(args.original), decode(args.capture)
    original -= original.mean()
    capture -= capture.mean()
    # Full waveform correlation checks source identity and capture offset.
    cross = correlate(capture, original, mode="full", method="fft")
    lag = int(correlation_lags(len(capture), len(original), mode="full")[np.argmax(cross)])
    capture_start, original_start = max(0, lag), max(0, -lag)
    shared = min(len(capture) - capture_start, len(original) - original_start)
    a, b = capture[capture_start:capture_start + shared], original[original_start:original_start + shared]
    similarity = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))) if shared else 0.0
    print(json.dumps({"original_seconds": round(len(original) / 8000, 3),
                      "capture_seconds": round(len(capture) / 8000, 3),
                      "capture_offset_seconds": round(lag / 8000, 3),
                      "overlap_seconds": round(shared / 8000, 3),
                      "waveform_correlation": round(similarity, 4)}))


if __name__ == "__main__":
    main()
