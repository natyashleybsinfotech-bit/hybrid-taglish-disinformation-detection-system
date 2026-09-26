"""EasyOCR, FFmpeg, and Whisper text acquisition for user-submitted media."""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import tempfile
import types
import wave
from pathlib import Path
from threading import Lock

import config


class MediaProcessingError(RuntimeError):
    """A safe, user-presentable media processing failure."""


_ocr_reader = None
_whisper_model = None
_ocr_lock = Lock()
_whisper_lock = Lock()


def _normalize_parts(parts: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for part in parts:
        clean = re.sub(r"\s+", " ", str(part)).strip()
        key = clean.casefold()
        if clean and key not in seen:
            seen.add(key)
            normalized.append(clean)
    return normalized


def combine_text(*groups: list[str]) -> str:
    return "\n".join(_normalize_parts([part for group in groups for part in group]))


def _prepare_easyocr_import() -> None:
    """Use pure-Python BiDi when Windows blocks the optional native extension."""
    try:
        import bidi
        if not hasattr(bidi, "get_display"):
            from bidi.algorithm import get_display
            bidi.get_display = get_display
    except ImportError as exc:
        raise MediaProcessingError("EasyOCR text support is unavailable.") from exc


def _get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is not None:
        return _ocr_reader
    with _ocr_lock:
        if _ocr_reader is None:
            try:
                _prepare_easyocr_import()
                import easyocr
                config.MEDIA_MODEL_DIR.mkdir(parents=True, exist_ok=True)
                _ocr_reader = easyocr.Reader(
                    list(config.OCR_LANGUAGES),
                    gpu=config.OCR_GPU,
                    model_storage_directory=str(config.MEDIA_MODEL_DIR / "easyocr"),
                    verbose=False,
                )
            except Exception as exc:
                raise MediaProcessingError("EasyOCR could not be initialized.") from exc
    return _ocr_reader


def _prepare_whisper_import() -> None:
    """Provide Whisper's two JIT decorators when Numba DLLs are policy-blocked."""
    try:
        import numba  # noqa: F401
        return
    except Exception:
        module = types.ModuleType("numba")

        def jit(*_args, **_kwargs):
            def decorator(function):
                return function
            return decorator

        module.jit = jit
        sys.modules["numba"] = module


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    with _whisper_lock:
        if _whisper_model is None:
            try:
                _prepare_whisper_import()
                import whisper
                config.MEDIA_MODEL_DIR.mkdir(parents=True, exist_ok=True)
                _whisper_model = whisper.load_model(
                    config.WHISPER_MODEL_NAME,
                    download_root=str(config.MEDIA_MODEL_DIR / "whisper"),
                )
            except Exception as exc:
                raise MediaProcessingError("Whisper could not be initialized.") from exc
    return _whisper_model


def ffmpeg_executable() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise MediaProcessingError("FFmpeg is unavailable.") from exc


def service_health() -> dict:
    ffmpeg_available = False
    try:
        ffmpeg_available = Path(ffmpeg_executable()).is_file()
    except MediaProcessingError:
        pass
    return {
        "easyocr": "available" if importlib.util.find_spec("easyocr") else "unavailable",
        "whisper": "available" if importlib.util.find_spec("whisper") else "unavailable",
        "ffmpeg": "available" if ffmpeg_available else "unavailable",
        "whisper_model": config.WHISPER_MODEL_NAME,
    }


def extract_image_text(image_bytes: bytes) -> dict:
    if not image_bytes:
        raise MediaProcessingError("The image file is empty.")
    if len(image_bytes) > config.MAX_MEDIA_BYTES:
        raise MediaProcessingError("The image exceeds the configured upload limit.")
    try:
        import cv2
        import numpy as np
        image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise MediaProcessingError("The image format is unreadable or unsupported.")
        lines = _normalize_parts(_get_ocr_reader().readtext(image, detail=0, paragraph=False))
    except MediaProcessingError:
        raise
    except Exception as exc:
        raise MediaProcessingError("EasyOCR could not extract text from the image.") from exc
    if not lines:
        raise MediaProcessingError("No readable text was found in the image.")
    return {"extraction_status": "completed", "ocr_text": "\n".join(lines), "lines": lines}


def _run_ffmpeg(arguments: list[str]) -> None:
    result = subprocess.run(
        [ffmpeg_executable(), "-hide_banner", "-loglevel", "error", "-y", *arguments],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise MediaProcessingError("FFmpeg could not process the submitted video.")


def _read_pcm_wave(path: Path):
    """Read the normalized 16-bit mono WAV without Whisper spawning system FFmpeg."""
    try:
        import numpy as np
        with wave.open(str(path), "rb") as stream:
            if stream.getnchannels() != 1 or stream.getsampwidth() != 2:
                raise MediaProcessingError("The extracted audio format is unsupported.")
            samples = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2")
        return samples.astype(np.float32) / 32768.0
    except MediaProcessingError:
        raise
    except Exception as exc:
        raise MediaProcessingError("The extracted audio could not be decoded.") from exc


def process_video(video_bytes: bytes, suffix: str = ".mp4") -> dict:
    if not video_bytes:
        raise MediaProcessingError("The video file is empty.")
    if len(video_bytes) > config.MAX_MEDIA_BYTES:
        raise MediaProcessingError("The video exceeds the configured upload limit.")
    config.TEMP_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=config.TEMP_MEDIA_DIR) as temp_name:
        temp_dir = Path(temp_name)
        video_path = temp_dir / f"input{suffix}"
        audio_path = temp_dir / "audio.wav"
        frame_pattern = temp_dir / "frame-%03d.jpg"
        video_path.write_bytes(video_bytes)
        _run_ffmpeg(["-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000", str(audio_path)])
        interval = max(1, config.VIDEO_FRAME_INTERVAL_SECONDS)
        _run_ffmpeg([
            "-i", str(video_path), "-vf", f"fps=1/{interval}", "-frames:v",
            str(max(1, config.VIDEO_MAX_FRAMES)), str(frame_pattern),
        ])
        try:
            transcription = _get_whisper_model().transcribe(_read_pcm_wave(audio_path), fp16=False)
            transcript_parts = _normalize_parts([str(transcription.get("text", ""))])
        except MediaProcessingError:
            raise
        except Exception as exc:
            raise MediaProcessingError("Whisper could not transcribe the video audio.") from exc

        frame_parts: list[str] = []
        for frame in sorted(temp_dir.glob("frame-*.jpg")):
            try:
                frame_parts.extend(extract_image_text(frame.read_bytes())["lines"])
            except MediaProcessingError:
                continue
        combined = combine_text(transcript_parts, frame_parts)
        if not combined:
            raise MediaProcessingError("No usable speech or on-screen text was extracted.")
        return {
            "extraction_status": "completed",
            "transcript_text": "\n".join(transcript_parts),
            "frame_ocr_text": "\n".join(_normalize_parts(frame_parts)),
            "analyzed_text": combined,
            "sampled_frames": len(list(temp_dir.glob("frame-*.jpg"))),
        }
