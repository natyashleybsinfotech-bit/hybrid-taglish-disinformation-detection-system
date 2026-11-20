"""EasyOCR, FFmpeg, and Whisper text acquisition for user-submitted media."""

from __future__ import annotations

import copy
import hashlib
import json
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import io
import math
import re
import subprocess
import sys
import tempfile
import types
import wave
from pathlib import Path
from threading import Lock, Timer

import config
try:
    from .gemini_audio import transcribe_audio
except ImportError:
    from gemini_audio import transcribe_audio


class MediaProcessingError(RuntimeError):
    """A safe, user-presentable media processing failure."""


class SpeechServiceError(MediaProcessingError):
    """A failed provider request is not bad speech and must not become a prediction."""
    def __init__(self, status):
        self.status = status
        super().__init__("The audio transcription service could not complete. Please retry.")


class SpeechQualityError(MediaProcessingError):
    """Speech diagnostics failed; this is distinct from infrastructure/media errors."""


_ocr_reader = None
_whisper_model = None
_ocr_lock = Lock()
_ocr_inference_lock = Lock()
_whisper_lock = Lock()
_video_cache_lock = Lock()
_video_cache = OrderedDict()
_video_cache_timers = {}
_VIDEO_CACHE_MAX_ENTRIES = 2
_VIDEO_CACHE_MAX_BYTES = 1024 * 1024


def clear_video_extraction_cache():
    with _video_cache_lock:
        _video_cache.clear()
        for timer in _video_cache_timers.values():
            timer.cancel()
        _video_cache_timers.clear()


def _expire_video_cache(key, expiration):
    with _video_cache_lock:
        item = _video_cache.get(key)
        if item and item[0] == expiration:
            del _video_cache[key]
            _video_cache_timers.pop(key, None)


def warm_media_engines():
    """Load the configured engines once in this API worker, without a prediction."""
    started = time.perf_counter()
    state = {}
    loaders = [("image_text", _get_ocr_reader)]
    if config.SPEECH_PROVIDER == "local": loaders.insert(0, ("speech", _get_whisper_model))
    for name, loader in loaders:
        stage = time.perf_counter()
        try:
            loader()
            state[name] = {"status": "ready", "load_ms": round((time.perf_counter()-stage)*1000, 3)}
        except Exception:
            state[name] = {"status": "unavailable"}
    return {"engines": state, "total_ms": round((time.perf_counter()-started)*1000, 3)}


def _video_cache_key(video_bytes, suffix, caption_fallback_allowed=False):
    settings = {name: getattr(config, name) for name in dir(config)
                if name.startswith(("TRANSCRIPT_", "WHISPER_", "OCR_")) and name != "WHISPER_API_KEY"}
    settings.update({"max_frames":config.VIDEO_MAX_FRAMES, "frame_interval":config.VIDEO_FRAME_INTERVAL_SECONDS,
                     "max_seconds":config.VIDEO_MAX_SECONDS, "model_dir":str(config.MEDIA_MODEL_DIR), "suffix":suffix,
                     "pipeline_revision":"video-extraction-v5-parallel-frame-read", "speech_provider":config.SPEECH_PROVIDER, "gemini_model":config.GEMINI_MODEL, "caption_fallback_allowed":caption_fallback_allowed})
    digest = hashlib.sha256(json.dumps(settings, sort_keys=True, default=str).encode())
    digest.update(video_bytes)
    return digest.hexdigest()


def process_video(video_bytes: bytes, suffix: str = ".mp4", caption_fallback_allowed: bool = False) -> dict:
    """Cache only complete successful extraction in bounded worker RAM, never predictions."""
    started = time.perf_counter()
    if not video_bytes:
        raise MediaProcessingError("The video file is empty.")
    if len(video_bytes) > config.MAX_MEDIA_BYTES:
        raise MediaProcessingError("The video exceeds the configured upload limit.")
    enabled = config.VIDEO_EXTRACTION_CACHE_ENABLED
    key = _video_cache_key(video_bytes, suffix, caption_fallback_allowed) if enabled else None
    now = time.monotonic()
    if enabled:
        with _video_cache_lock:
            for expired in [k for k, item in _video_cache.items() if item[0] <= now]:
                del _video_cache[expired]
                timer = _video_cache_timers.pop(expired, None)
                if timer: timer.cancel()
            if key in _video_cache:
                expires, stored, size = _video_cache[key]
                _video_cache.move_to_end(key)
                result = copy.deepcopy(stored)
                result["original_processing_timings_ms"] = result.pop("processing_timings_ms", {})
                result["processing_timings_ms"] = {"total":round((time.perf_counter()-started)*1000,3)}
                result["extraction_cache_hit"] = True
                return result
    result = _process_video_uncached(video_bytes, suffix, caption_fallback_allowed)
    result["extraction_cache_hit"] = False
    result.setdefault("processing_timings_ms", {})["total"] = round((time.perf_counter()-started)*1000,3)
    if enabled and result.get("extraction_status") == "completed":
        size = len(json.dumps(result, default=str).encode())
        if size <= _VIDEO_CACHE_MAX_BYTES:
            with _video_cache_lock:
                old_timer = _video_cache_timers.pop(key, None)
                if old_timer: old_timer.cancel()
                expiration = time.monotonic()+config.VIDEO_EXTRACTION_CACHE_TTL_SECONDS
                _video_cache[key] = (expiration, copy.deepcopy(result), size)
                timer = Timer(config.VIDEO_EXTRACTION_CACHE_TTL_SECONDS, _expire_video_cache, args=(key, expiration))
                timer.daemon = True
                _video_cache_timers[key] = timer
                timer.start()
                _video_cache.move_to_end(key)
                while len(_video_cache)>_VIDEO_CACHE_MAX_ENTRIES or sum(v[2] for v in _video_cache.values())>_VIDEO_CACHE_MAX_BYTES:
                    removed_key, _ = _video_cache.popitem(last=False)
                    old_timer = _video_cache_timers.pop(removed_key, None)
                    if old_timer: old_timer.cancel()
    return result



class _FasterWhisperAdapter:
    """Present CTranslate2's measured segments to the existing quality gate."""

    def __init__(self, model):
        self.model = model

    def transcribe(self, audio, **options) -> dict:
        options.pop("fp16", None)  # CTranslate2 chooses INT8 when the model loads.
        options["log_prob_threshold"] = options.pop("logprob_threshold")
        # Low-threshold speech detection keeps quieter speech and gives the
        # decoder pauses as boundaries. Faster-whisper restores segment times
        # to the original audio; completeness checks still use those times.
        options["vad_filter"] = True
        options["vad_parameters"] = {
            "threshold": 0.35, "min_silence_duration_ms": 750, "speech_pad_ms": 400,
        }
        segments, info = self.model.transcribe(audio, **options)
        rows = []
        for item in segments:
            rows.append({"text": item.text, "start": item.start, "end": item.end,
                         "avg_logprob": item.avg_logprob, "no_speech_prob": item.no_speech_prob,
                         "compression_ratio": item.compression_ratio})
            try:
                _speech_segments({"segments":rows})
            except SpeechQualityError:
                # Preserve the rejected segment so the normal gate still fails.
                # Stop decoding later chunks which cannot repair that failure.
                close = getattr(segments, "close", None)
                if close: close()
                break
        return {"language": info.language, "segments": rows,
                "text": " ".join(row["text"].strip() for row in rows).strip()}


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


def _speech_frame_consistent(speech: list[str], frame_text: list[str]) -> bool:
    """Reject obvious topic mismatch; agreement does not certify word accuracy."""
    common = {"ang", "at", "mga", "ng", "na", "sa", "si", "sina", "ni", "the", "and", "for", "of", "to", "rep"}
    def terms(parts, *, include_compounds=False):
        words = re.findall(r"[^\W_]+", " ".join(parts).casefold())
        salient = {word for word in words if len(word) >= 3 and word not in common}
        # Captions may write one compound as two speech tokens (cyberlibel /
        # cyber libel). This changes only topic comparison, never OCR/ASR text.
        if include_compounds:
            salient.update(words[index] + words[index + 1] for index in range(len(words) - 1)
                           if len(words[index]) >= 3 and len(words[index + 1]) >= 3
                           and words[index] not in common and words[index + 1] not in common)
        return salient
    visible = terms(frame_text)
    shared = visible & terms(speech, include_compounds=True)
    # A few generic topic words can coexist with wrong people or events.
    # Require most salient headline words to appear in the speech before
    # allowing OCR and ASR to become one classification input.
    return bool(visible) and len(shared) >= min(3, len(visible)) and len(shared) / len(visible) >= 0.70


def _story_frame_detections(detections, width: int, height: int, sample_seconds: float,
                            speech: list[str] | None = None) -> tuple[list[dict], int]:
    """Keep readable story overlays; omit fixed broadcast chrome and ticker bands.

    Geometry is only a conservative acquisition filter. It does not verify that
    a headline supports the spoken claim, and excluded text is never inferred.
    """
    retained = []
    rejected = 0
    spoken_terms = set(re.findall(r"[^\W_]+", " ".join(speech or []).casefold()))
    for detection in detections:
        try:
            box, value, confidence = detection
            text = re.sub(r"\s+", " ", str(value)).strip()
            score = float(confidence)
            center_x = sum(float(point[0]) for point in box) / 4 / width
            center_y = sum(float(point[1]) for point in box) / 4 / height
            readable = sum(character.isalnum() for character in text)
            line_terms = {word for word in re.findall(r"[^\W_]+", text.casefold()) if len(word) >= 3}
            shared = line_terms & spoken_terms
            # A bottom-center subtitle can be actual spoken content. Require
            # direct word agreement before retaining it; unrelated tickers at
            # the same height still fail closed.
            subtitle = (center_y >= 0.90 and 0.22 <= center_x <= 0.78
                        and len(line_terms) >= 2 and len(shared) >= 2
                        and len(shared) / len(line_terms) >= 0.70)
            logo_or_end_card = bool(re.search(
                r"\b(?:thanks for [vw]atching|follow and subscribe|subscribe|news online|regional tv)\b",
                text, re.IGNORECASE,
            )) or bool(re.fullmatch(r"(?:GMA(?: NEWS| NETWORK)?|ABS[ -]?CBN(?: NEWS)?|TV PATROL|24 ORAS|PTV|NEWS 5)", text, re.IGNORECASE))
            excluded = (not math.isfinite(score) or score < config.OCR_MIN_CONFIDENCE
                        or readable < 8 or center_y < 0.25 or (center_y >= 0.90 and not subtitle)
                        or (center_x < 0.22 and center_y >= 0.70)
                        or logo_or_end_card)
        except (TypeError, ValueError, IndexError, ZeroDivisionError):
            excluded = True
        if excluded:
            rejected += 1
            continue
        retained.append({"text": text, "confidence": score,
                         "sample_seconds": round(sample_seconds, 2),
                         "region_type": "subtitle" if subtitle else "story_text",
                         "box": [[round(float(x), 1), round(float(y), 1)] for x, y in box]})
    return retained, rejected


def _usable_ocr_lines(detections) -> tuple[list[str], int]:
    """Keep measured OCR detections, not unscored strings or unreadable fragments."""
    accepted = []
    rejected = 0
    for detection in detections:
        try:
            _box, value, confidence = detection
            text = str(value).strip()
            visible = [char for char in text if not char.isspace()]
            readable = sum(char.isalnum() for char in visible)
            if (not math.isfinite(float(confidence)) or float(confidence) < config.OCR_MIN_CONFIDENCE or not visible
                    or readable < 2 or readable / len(visible) < 0.5):
                rejected += 1
                continue
        except (TypeError, ValueError):
            rejected += 1
            continue
        accepted.append(text)
    return _normalize_parts(accepted), rejected


def _speech_segments(transcription: dict) -> list[dict]:
    """Reject an uncertain transcript instead of silently screening partial speech.

    Whisper's diagnostics are quality gates, never proof of word accuracy.
    Do not repair the wording, translate it, or use a prompt to invent context.
    """
    segments = transcription.get("segments")
    if not isinstance(segments, list):
        raise SpeechQualityError("Speech quality could not be checked. Try a clearer video or use its complete caption.")
    accepted = []
    for segment in segments:
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        try:
            start, end = float(segment["start"]), float(segment["end"])
            logprob = float(segment["avg_logprob"])
            no_speech = float(segment["no_speech_prob"])
            compression = float(segment["compression_ratio"])
            values = (start, end, logprob, no_speech, compression)
            if not all(math.isfinite(value) for value in values):
                raise ValueError("Non-finite speech diagnostics")
            tokens = re.findall(r"\w+", text.casefold())
            triples = [tuple(tokens[i:i + 3]) for i in range(max(0, len(tokens) - 2))]
            repetitive = len(tokens) >= 12 and len(set(triples)) / len(triples) < 0.45
            uncertain = (start < 0 or end <= start or logprob < config.TRANSCRIPT_MIN_AVG_LOGPROB
                         or no_speech >= config.TRANSCRIPT_MAX_NO_SPEECH_PROB
                         or compression > config.TRANSCRIPT_MAX_COMPRESSION_RATIO or repetitive
                         or not any(char.isalnum() for char in text))
        except (KeyError, TypeError, ValueError):
            uncertain = True
        if uncertain:
            raise SpeechQualityError("Some speech could not be transcribed clearly. No prediction was made from the uncertain transcript. Try a clearer clip or check the complete caption instead.")
        if accepted and start - accepted[-1]["end_seconds"] > 8:
            raise SpeechQualityError("A substantial middle section of the video speech was not transcribed. No prediction was made from an incomplete transcript.")
        accepted.append({"start_seconds": start, "end_seconds": end, "text": text})
    return accepted


def _transcription_language(model, audio) -> tuple[str | None, str]:
    """Use auto detection only for clearly English long clips.

    Sample three parts of the *audio*, not its caption. Mixed/uncertain clips
    keep the Filipino hint so Filipino speech is not translated to English.
    """
    configured = config.WHISPER_LANGUAGE_HINT
    if (configured != "tl" or config.WHISPER_ENGINE != "faster-whisper"
            or not isinstance(model, _FasterWhisperAdapter)
            or len(audio) < 60 * 16000):
        return (None if configured == "auto" else configured), "configured"
    try:
        from faster_whisper.vad import VadOptions
        window = 20 * 16000
        offsets = [0, (len(audio) - window) // 2, len(audio) - window]
        vad = VadOptions(threshold=.35, min_silence_duration_ms=750, speech_pad_ms=400)
        # English requires all three probes. Once one fails, remaining probes
        # cannot change the decision, so avoid redundant encoder passes.
        for start in offsets:
            language, probability = model.model.detect_language(
                audio[start:start + window], vad_filter=True, vad_parameters=vad)[:2]
            if not (language == "en" and probability >= .95):
                return "tl", "configured"
        return None, "detected_english"
    except Exception:
        pass  # Detection is advisory; the configured decoder remains available.
    return "tl", "configured"


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
                config.MEDIA_MODEL_DIR.mkdir(parents=True, exist_ok=True)
                if config.WHISPER_ENGINE == "faster-whisper":
                    from faster_whisper import WhisperModel
                    _whisper_model = _FasterWhisperAdapter(WhisperModel(
                        config.WHISPER_MODEL_NAME, device="cpu", compute_type="int8",
                        download_root=str(config.MEDIA_MODEL_DIR / "faster-whisper"),
                    ))
                elif config.WHISPER_ENGINE == "openai-whisper":
                    _prepare_whisper_import()
                    import whisper
                    _whisper_model = whisper.load_model(
                        config.WHISPER_MODEL_NAME,
                        download_root=str(config.MEDIA_MODEL_DIR / "whisper"),
                    )
                else:
                    raise ValueError("Unsupported local speech-recognition engine")
            except Exception as exc:
                raise MediaProcessingError("Local speech recognition could not be initialized.") from exc
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
        "whisper": "available" if importlib.util.find_spec(
            "faster_whisper" if config.WHISPER_ENGINE == "faster-whisper" else "whisper"
        ) else "unavailable",
        "ffmpeg": "available" if ffmpeg_available else "unavailable",
        "speech_provider": config.SPEECH_PROVIDER,
        "remote_speech_configured": config.SPEECH_PROVIDER == "gemini" and bool(config.GEMINI_ENABLED and config.GEMINI_API_KEY),
        "speech_engine_loaded": _whisper_model is not None,
        "ocr_engine_loaded": _ocr_reader is not None,
        "video_extraction_cache_enabled": config.VIDEO_EXTRACTION_CACHE_ENABLED,
        "whisper_engine": config.WHISPER_ENGINE,
        "whisper_model": config.WHISPER_MODEL_NAME,
        "whisper_language_hint": config.WHISPER_LANGUAGE_HINT,
        "whisper_vad_filter": config.WHISPER_ENGINE == "faster-whisper",
        "whisper_previous_text_context": config.WHISPER_ENGINE == "faster-whisper",
    }


def extract_image_text(image_bytes: bytes) -> dict:
    if not image_bytes:
        raise MediaProcessingError("The image file is empty.")
    if len(image_bytes) > config.MAX_MEDIA_BYTES:
        raise MediaProcessingError("The image exceeds the configured upload limit.")
    try:
        from PIL import Image
        with Image.open(io.BytesIO(image_bytes)) as preview:
            if preview.width * preview.height > 20_000_000:
                raise MediaProcessingError("Image exceeds the 20-megapixel processing limit.")
        import cv2
        import numpy as np
        image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise MediaProcessingError("The image format is unreadable or unsupported.")
        lines, discarded = _usable_ocr_lines(_get_ocr_reader().readtext(image, detail=1, paragraph=False))
    except MediaProcessingError:
        raise
    except Exception as exc:
        raise MediaProcessingError("The image is unreadable or text extraction failed.") from exc
    if not lines:
        raise MediaProcessingError("No readable text was found in the image.")
    return {"extraction_status": "completed", "ocr_text": "\n".join(lines), "lines": lines,
            "discarded_ocr_detections": discarded}


def _run_ffmpeg(arguments: list[str], *, timeout: float = 240) -> None:
    try:
        result = subprocess.run(
            [ffmpeg_executable(), "-hide_banner", "-loglevel", "error", "-y", *arguments],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise MediaProcessingError("Media decoding timed out. Submit a shorter clip.") from None
    if result.returncode != 0:
        raise MediaProcessingError("FFmpeg could not process the submitted video.")


def _read_pcm_wave(path: Path):
    """Read the normalized 16-bit mono WAV without Whisper spawning system FFmpeg."""
    try:
        import numpy as np
        with wave.open(str(path), "rb") as stream:
            if stream.getnchannels() != 1 or stream.getsampwidth() != 2:
                raise MediaProcessingError("The extracted audio format is unsupported.")
            # AAC can add a fraction of a second of decoded padding to an exact-limit clip.
            if stream.getnframes() / stream.getframerate() > config.VIDEO_MAX_SECONDS + 0.25:
                raise MediaProcessingError("Video audio exceeds the 180-second limit. Submit a shorter clip.")
            samples = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2")
        return samples.astype(np.float32) / 32768.0
    except MediaProcessingError:
        raise
    except Exception as exc:
        raise MediaProcessingError("The extracted audio could not be decoded.") from exc


def _read_video_frames(frames):
    """Acquire OCR independently of speech; relevance filtering happens later."""
    started = time.perf_counter()
    readings = []
    for frame in frames:
        try:
            import cv2
            image = cv2.imread(str(frame))
            if image is None:
                readings.append((frame.name, 0, 0, None))
                continue
            height, width = image.shape[:2]
            reader = _get_ocr_reader()
            with _ocr_inference_lock:
                detections = reader.readtext(image, detail=1, paragraph=False)
            readings.append((frame.name, width, height, detections))
        except Exception:
            readings.append((frame.name, 0, 0, None))
    return readings, (time.perf_counter() - started) * 1000


def _process_video_uncached(video_bytes: bytes, suffix: str = ".mp4", caption_fallback_allowed: bool = False) -> dict:
    timings = {}
    stage = time.perf_counter()
    if not video_bytes:
        raise MediaProcessingError("The video file is empty.")
    if len(video_bytes) > config.MAX_MEDIA_BYTES:
        raise MediaProcessingError("The video exceeds the configured upload limit.")
    config.TEMP_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=config.TEMP_MEDIA_DIR) as temp_name:
        temp_dir = Path(temp_name)
        video_path = temp_dir / f"input{suffix}"
        audio_path = temp_dir / "audio.wav"
        video_path.write_bytes(video_bytes)
        _run_ffmpeg(["-protocol_whitelist", "file,pipe", "-format_whitelist", "mov,matroska,webm,avi", "-i", str(video_path), "-t", str(config.VIDEO_MAX_SECONDS + 1), "-vn", "-ac", "1", "-ar", "16000", str(audio_path)])
        audio = _read_pcm_wave(audio_path)  # Reject overlong clips before transcription.
        timings["audio_prepare"] = round((time.perf_counter()-stage)*1000,3)
        stage = time.perf_counter()
        # Seek each frame explicitly. The fps filter may shift the first output
        # frame and its enumeration is not a reliable timestamp for OCR review.
        duration = len(audio) / 16000
        frame_count = min(max(1, config.VIDEO_MAX_FRAMES),
                          max(1, math.ceil(duration / max(1, config.VIDEO_FRAME_INTERVAL_SECONDS))))
        sample_times: dict[str, float] = {}
        for index in range(frame_count):
            second = min(max(0, duration - 0.1), (index + 0.5) * duration / frame_count)
            frame = temp_dir / f"frame-{index + 1:03d}.jpg"
            _run_ffmpeg([
                "-ss", str(round(second, 3)), "-protocol_whitelist", "file,pipe",
                "-format_whitelist", "mov,matroska,webm,avi", "-i", str(video_path),
                "-frames:v", "1", str(frame),
            ])
            sample_times[frame.name] = second
        timings["frame_sampling"] = round((time.perf_counter()-stage)*1000,3)
        frames = sorted(temp_dir.glob("frame-*.jpg"))
        ocr_pool = None
        ocr_task = None
        # Remote speech waits on network I/O. Read the same sampled frames in
        # that interval, while retaining one complete audio transcription.
        # Local Whisper shares CPU resources with OCR, so keep it sequential.
        if config.SPEECH_PROVIDER == "gemini":
            ocr_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="suriph-frame-ocr")
            ocr_task = ocr_pool.submit(_read_video_frames, frames)
        try:
            import numpy as np
            silent = not len(audio) or float(np.max(np.abs(audio))) <= 0.0001
            segments = []
            speech_language = None
            speech_language_mode = "none"
            if not silent:
                if config.SPEECH_PROVIDER == "gemini":
                    stage = time.perf_counter()
                    response = transcribe_audio(audio_path.read_bytes(), duration)
                    timings["speech_transcription"] = round((time.perf_counter()-stage)*1000,3)
                    if response.get("status") in {"unclear", "no_speech"}:
                        raise SpeechQualityError("The audio could not be transcribed clearly. Compare the original video or use its complete caption.")
                    if response.get("status") != "transcribed":
                        raise SpeechServiceError(response.get("status", "unavailable"))
                    segments = response["segments"]
                    speech_language = response["language"]
                    speech_language_mode = "external_audio_chunks"
                else:
                    stage = time.perf_counter()
                    model = _get_whisper_model()
                    timings["speech_model_load"] = round((time.perf_counter()-stage)*1000,3)
                    stage = time.perf_counter()
                    language_choice, speech_language_mode = _transcription_language(model, audio)
                    timings["language_detection"] = round((time.perf_counter()-stage)*1000,3)
                    stage = time.perf_counter()
                    options = dict(
                        fp16=False, task="transcribe",
                        condition_on_previous_text=config.WHISPER_ENGINE == "faster-whisper",
                        temperature=0.0,
                        word_timestamps=True, hallucination_silence_threshold=2.0,
                        no_speech_threshold=config.TRANSCRIPT_MAX_NO_SPEECH_PROB,
                        logprob_threshold=config.TRANSCRIPT_MIN_AVG_LOGPROB,
                        compression_ratio_threshold=config.TRANSCRIPT_MAX_COMPRESSION_RATIO,
                    )
                    transcription = model.transcribe(
                        audio, language=language_choice,
                        **options,
                    )
                    if transcription.get("language") not in {"tl", "en", "ceb"}:
                        raise SpeechQualityError(
                            "The video's speech language could not be identified as Filipino or English reliably. "
                            "No prediction was made from this transcript."
                        )
                    try:
                        segments = _speech_segments(transcription)
                    except MediaProcessingError as original_error:
                        # English speech can produce repeated words under a
                        # Filipino hint. Retry once, preserving the actual audio.
                        # Accept only a clean English result; Filipino failures
                        # still return an extraction error.
                        if caption_fallback_allowed:
                            raise
                        if config.WHISPER_ENGINE != "faster-whisper" or language_choice != "tl":
                            raise
                        candidate = model.transcribe(audio, language=None, **options)
                        if candidate.get("language") != "en":
                            raise original_error
                        segments = _speech_segments(candidate)
                        transcription = candidate
                        speech_language_mode = "auto_retry_after_quality_failure"
                    timings["speech_transcription"] = round((time.perf_counter()-stage)*1000,3)
                    speech_language = transcription.get("language")
            transcript_parts = _normalize_parts([segment["text"] for segment in segments])
            if not silent and not transcript_parts:
                raise SpeechQualityError("No reliable speech was extracted from the video's audible track. No prediction was made from frame text alone.")
        except MediaProcessingError:
            raise
        except Exception as exc:
            raise MediaProcessingError("Whisper could not transcribe the video audio.") from exc
        finally:
            if ocr_pool:
                wait_started = time.perf_counter()
                # Join before temporary files are removed, including errors.
                ocr_pool.shutdown(wait=True, cancel_futures=True)
                timings["frame_ocr_wait_after_speech"] = round((time.perf_counter()-wait_started)*1000,3)

        readings, ocr_ms = ocr_task.result() if ocr_task else _read_video_frames(frames)
        stage = time.perf_counter()
        frame_parts: list[str] = []
        frame_regions: list[dict] = []
        discarded_ocr = 0
        failed_frames = 0
        read_frames = 0
        for frame_name, width, height, detections in readings:
            if detections is None:
                failed_frames += 1
                continue
            try:
                regions, rejected = _story_frame_detections(
                    detections, width, height, sample_times[frame_name], transcript_parts,
                )
                frame_regions.extend(regions)
                frame_parts.extend(region["text"] for region in regions)
                discarded_ocr += rejected
                read_frames += 1
            except Exception:
                failed_frames += 1
        timings["frame_ocr"] = round(ocr_ms + (time.perf_counter()-stage)*1000,3)
        frame_status = ('partial' if read_frames else 'failed') if failed_frames else (
            'completed' if frame_parts else 'no_readable_text')
        frame_agreement = not (transcript_parts and frame_parts) or _speech_frame_consistent(transcript_parts, frame_parts)
        quality_notice = "Automatic speech and image-text extraction can miss or misread words. Compare the extracted text with the original video. Only sampled frames were checked."
        if failed_frames:
            quality_notice += f" Text could not be read from {failed_frames} sampled frame(s). The video text extraction is incomplete."
        if not frame_agreement:
            # Different languages and quoted statements can have low word overlap.
            # Return both originals for the existing explicit review step instead
            # of treating lexical disagreement as a failed audio extraction.
            quality_notice += " The speech and on-screen wording differ. Check both against the video before confirming. Frame text was excluded from the classifier input."
        # A visible overlay can describe another story. Preserve it for review,
        # but never silently add it to the classifier input when it cannot be
        # tied to the spoken story by direct word overlap.
        frame_ocr_included = bool(frame_parts) and (not transcript_parts or frame_agreement)
        combined = combine_text(transcript_parts, frame_parts if frame_ocr_included else [])
        if not combined:
            raise MediaProcessingError("No usable speech or on-screen text was extracted.")
        return {
            "processing_timings_ms": timings,
            "extraction_status": "partial" if failed_frames else "completed",
            "transcript_text": "\n".join(transcript_parts),
            "frame_ocr_text": "\n".join(_normalize_parts(frame_parts)),
            "frame_ocr_regions": frame_regions,
            "analyzed_text": combined,
            "sampled_frames": len(list(temp_dir.glob("frame-*.jpg"))),
            "frame_ocr_status": frame_status,
            "failed_ocr_frames": failed_frames,
            "transcript_segments": segments,
            "transcript_status": "completed" if transcript_parts else "no_reliable_speech",
            "speech_language": speech_language,
            "speech_language_mode": speech_language_mode,
            "transcript_source": "external_audio" if config.SPEECH_PROVIDER == "gemini" else "local_whisper",
            "timestamp_basis": "server_audio_chunks" if config.SPEECH_PROVIDER == "gemini" else "decoder_segments",
            "speech_frame_agreement": "word_overlap" if frame_agreement else "review_required",
            "frame_ocr_included": frame_ocr_included,
            "discarded_ocr_detections": discarded_ocr,
            "quality_notice": quality_notice,
        }
