import os
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
        fake_image = Mock()
        reader = Mock()
        reader.readtext.return_value = ["Visible text", "visible   text", "Dagdag"]
        with patch("media_processing._get_ocr_reader", return_value=reader), patch(
            "cv2.imdecode", return_value=fake_image
        ):
            result = media_processing.extract_image_text(b"image-bytes")
        self.assertEqual(result["extraction_status"], "completed")
        self.assertEqual(result["ocr_text"], "Visible text\nDagdag")

    def test_unreadable_image_has_clear_failure(self):
        with patch("cv2.imdecode", return_value=None):
            with self.assertRaisesRegex(media_processing.MediaProcessingError, "unreadable"):
                media_processing.extract_image_text(b"not-an-image")

    def test_service_health_reports_required_services(self):
        health = media_processing.service_health()
        self.assertEqual(set(health), {"easyocr", "whisper", "ffmpeg", "whisper_model"})


if __name__ == "__main__":
    unittest.main()
