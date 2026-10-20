import os
import io
import tempfile
import wave
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import media_processing


class MediaProcessingTests(unittest.TestCase):
    def test_combine_text_normalizes_and_deduplicates(self):
        result = media_processing.combine_text(
            ["  Isang claim   dito.  ", "Duplicate"], ["duplicate", "Frame text"]
        )
        self.assertEqual(result, "Isang claim dito.\nDuplicate\nFrame text")

    def test_image_flow_uses_easyocr_output(self):
        from PIL import Image
        image_bytes = io.BytesIO()
        Image.new('RGB', (5, 5), 'white').save(image_bytes, format='PNG')
        fake_image = Mock()
        reader = Mock()
        reader.readtext.return_value = ["Visible text", "visible   text", "Dagdag"]
        with patch("media_processing._get_ocr_reader", return_value=reader), patch(
            "cv2.imdecode", return_value=fake_image
        ):
            result = media_processing.extract_image_text(image_bytes.getvalue())
        self.assertEqual(result["extraction_status"], "completed")
        self.assertEqual(result["ocr_text"], "Visible text\nDagdag")

    def test_unreadable_image_has_clear_failure(self):
        with patch("cv2.imdecode", return_value=None):
            with self.assertRaisesRegex(media_processing.MediaProcessingError, "unreadable"):
                media_processing.extract_image_text(b"not-an-image")

    def test_service_health_reports_required_services(self):
        health = media_processing.service_health()
        self.assertEqual(set(health), {"easyocr", "whisper", "ffmpeg", "whisper_model"})

    def test_oversized_image_is_rejected_before_ocr(self):
        preview = Mock(width=5000, height=5000)
        preview.__enter__ = Mock(return_value=preview)
        preview.__exit__ = Mock(return_value=False)
        with patch('PIL.Image.open', return_value=preview), patch('media_processing._get_ocr_reader') as reader:
            with self.assertRaisesRegex(media_processing.MediaProcessingError, '20-megapixel'):
                media_processing.extract_image_text(b'fixture')
            reader.assert_not_called()

    def test_overlong_audio_is_rejected_without_partial_transcript(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'audio.wav')
            with wave.open(path, 'wb') as stream:
                stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(1); stream.writeframes(b'\0\0' * 121)
            with self.assertRaisesRegex(media_processing.MediaProcessingError, '120-second'):
                media_processing._read_pcm_wave(path)


if __name__ == "__main__":
    unittest.main()
