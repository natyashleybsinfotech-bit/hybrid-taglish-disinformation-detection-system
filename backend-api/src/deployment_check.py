"""Run inside the deployment container before accepting real traffic."""

import argparse
import json

import config
from . import database
from .model_runtime import runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--media", action="store_true", help="Warm OCR and Whisper and verify FFmpeg")
    args = parser.parse_args()
    config.validate_runtime_config()
    if database.database_health()["status"] != "available":
        raise RuntimeError("Run the isolated migration service before deployment checks")
    database.ensure_bootstrap_admin()
    database.ensure_bootstrap_viewer()
    health = runtime.initialize()
    if health["status"] != "ready":
        raise RuntimeError(health.get("error", "Model unavailable"))
    for sample in ("Isang balita para sa pagsusuri.", "This is a news screening test.", "Check muna natin ang source ng news."):
        runtime.predict(sample)
    if args.media:
        import subprocess
        from .media_processing import _get_ocr_reader, _get_whisper_model, ffmpeg_executable
        _get_ocr_reader()
        _get_whisper_model()
        subprocess.run([ffmpeg_executable(), "-version"], check=True, capture_output=True, timeout=20)
    print(json.dumps({"database": database.database_health(), "model": health, "inference_smoke": "passed", "media_warmup": args.media}, indent=2))


if __name__ == "__main__":
    main()
