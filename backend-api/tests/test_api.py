import io
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fastapi.testclient import TestClient

import app as application
from media_processing import MediaProcessingError


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(application.app)

    def setUp(self):
        self.retrieval_patcher = patch.object(
            application,
            "retrieve_related_sources",
            return_value={"retrieval_status": "disabled", "related_sources": []},
        )
        self.retrieval_patcher.start()
        self.fact_check_patcher = patch.object(
            application,
            "search_fact_checks",
            return_value={"status": "no_results", "matches": [], "signal": None},
        )
        self.fact_check_patcher.start()

    def tearDown(self):
        self.retrieval_patcher.stop()
        self.fact_check_patcher.stop()

    def test_health_is_available_when_database_is_offline(self):
        with patch.object(application.database, "database_health", return_value={
            "status": "unavailable", "engine": "mysql-mariadb"
        }):
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["database"]["status"], "unavailable")

    def test_text_contract_is_deterministic(self):
        payload = {"text": "Isang test claim for Sprint 1."}
        first = self.client.post("/analyze", json=payload)
        second = self.client.post("/analyze", json=payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["internal_label"], second.json()["internal_label"])
        self.assertEqual(first.json()["temporary_score"], second.json()["temporary_score"])
        self.assertEqual(first.json()["model_status"], "mock-prototype")
        self.assertIn("context_explanation", first.json())
        self.assertIn("fact_check_matches", first.json())
        self.assertEqual(first.json()["page_url"], None)
        self.assertIn(first.json()["public_label"], {
            "Potentially Misleading", "No Misleading Information Detected"
        })

    def test_close_google_fact_check_can_supply_the_single_overall_verdict(self):
        self.fact_check_patcher.stop()
        signal = {
            "internal_label": "Misleading",
            "public_label": "Potentially Misleading",
            "confidence": 0.91,
            "basis": "A closely matching published fact-check rated the claim as: False",
            "source_url": "https://example.org/fact-check",
        }
        with patch.object(application, "search_fact_checks", return_value={
            "status": "available",
            "matches": [{"url": signal["source_url"], "rating": "False"}],
            "signal": signal,
        }):
            response = self.client.post("/analyze", json={"text": "A closely matching claim"})
        self.fact_check_patcher.start()
        body = response.json()
        self.assertEqual(body["public_label"], "Potentially Misleading")
        self.assertEqual(body["decision_source"], "google_fact_check")
        self.assertEqual(body["decision_basis"], signal["basis"])

    def test_context_separates_statements_and_explains_recency(self):
        payload = {
            "text": "The first statement makes one claim. The second statement makes a different claim.",
            "context": {
                "author": "Example News",
                "published_text": "2h",
                "freshness": "Very recent",
                "extraction_scope": "Post text and readable image text",
            },
        }
        response = self.client.post("/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        explanation = response.json()["context_explanation"]
        self.assertEqual(explanation["author"], "Example News")
        self.assertIn("event itself is new", explanation["recency_explanation"])
        self.assertEqual(len(explanation["separate_statements"]), 2)
        self.assertEqual(explanation["checked_material"], "Post text and readable image text")

    def test_context_removes_repeated_facebook_ui_fragments(self):
        text = (
            "September 12, 2026... NEWS UPDATE DOLE approves P60 wage hike for minimum wage "
            "earners in Metro Manila effective Sept. 26 September 12, 2026 Read more "
            "#ReadMoreOnABSCBN.com on abs-cbn.com ABS-CBN NEWS NEWS UPDATE DOLE approves "
            "P60 wage hike for minimum wage earners in Metro Manila effective Sept."
        )
        explanation = application._context_explanation(text, {})
        self.assertEqual(explanation["separate_statements"], [])
        self.assertEqual(len(explanation["main_points"]), 0)
        self.assertIn("DOLE approves P60 wage hike", explanation["overview"])

    def test_image_text_reaches_same_screening_contract(self):
        extraction = {"extraction_status": "completed", "ocr_text": "OCR sample text"}
        with patch.object(application, "extract_image_text", return_value=extraction):
            response = self.client.post(
                "/analyze/image", files={"file": ("sample.png", io.BytesIO(b"png"), "image/png")}
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["input_type"], "image")
        self.assertEqual(response.json()["analyzed_text"], "OCR sample text")
        self.assertIn("context_explanation", response.json())
        self.assertIn(response.json()["public_label"], {
            "Potentially Misleading", "No Misleading Information Detected"
        })

    def test_video_text_reaches_same_screening_contract(self):
        extraction = {
            "extraction_status": "completed", "analyzed_text": "Transcript\nFrame text",
            "transcript_text": "Transcript", "frame_ocr_text": "Frame text", "sampled_frames": 1,
        }
        with patch.object(application, "process_video", return_value=extraction):
            response = self.client.post(
                "/analyze/video", files={"file": ("sample.mp4", io.BytesIO(b"video"), "video/mp4")}
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["input_type"], "video")
        self.assertIn("context_explanation", response.json())
        self.assertEqual(response.json()["extraction"]["sampled_frames"], 1)

    def test_media_failure_never_becomes_success(self):
        with patch.object(
            application, "extract_image_text", side_effect=MediaProcessingError("No readable text was found.")
        ):
            response = self.client.post(
                "/analyze/image", files={"file": ("sample.png", io.BytesIO(b"png"), "image/png")}
            )
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("public_label", response.json())

    def test_admin_login_and_protected_status(self):
        with patch.object(application.config, "SESSION_SECRET", "test-session-secret"), patch.object(
            application.database, "verify_admin",
            return_value={"id": 1, "username": "admin", "role": "admin"},
        ), patch.object(application.database, "log_audit", return_value=1):
            login = self.client.post("/admin-api/login", json={"username": "admin", "password": "test"})
        self.assertEqual(login.status_code, 200)
        with patch.object(application.config, "SESSION_SECRET", "test-session-secret"):
            status = self.client.get(
                "/admin-api/system-status",
                headers={"Authorization": f"Bearer {login.json()['token']}"},
            )
        self.assertEqual(status.status_code, 200)


if __name__ == "__main__":
    unittest.main()
