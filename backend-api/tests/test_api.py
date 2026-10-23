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


UNRESOLVED = {
    "assessment_status": "unresolved",
    "assessment_label": "Unresolved",
    "assessment_basis": "No closely matching published fact-check or related coverage was found.",
    "decision_source": "insufficient_evidence",
    "retrieval_status": "no_results",
    "related_sources": [],
    "fact_check_status": "no_results",
    "fact_check_matches": [],
}


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(application.app)

    def setUp(self):
        self.evidence_patcher = patch.object(application, "assess_evidence", return_value=UNRESOLVED.copy())
        self.evidence_mock = self.evidence_patcher.start()

    def tearDown(self):
        self.evidence_patcher.stop()

    def test_health_exposes_evidence_only_and_disabled_model(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["decision_engine"]["mode"], "evidence_only")
        self.assertFalse(body["decision_engine"]["classifier_loaded"])
        self.assertEqual(body["model"]["status"], "disabled")
        self.assertIsNone(body["model"]["classifier"])

    def test_readiness_requires_database_and_an_evidence_provider(self):
        with patch.object(application.database, "database_health", return_value={"status": "available"}), patch.object(
            application, "evidence_health", return_value={"status": "unavailable_not_configured", "ready": False, "mode": "evidence_only"}
        ):
            response = self.client.get("/ready")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["ready"])

    def test_analysis_never_returns_classifier_fields(self):
        text = "Ang tubig ay mahalaga sa katawan. Drinking enough water helps prevent dehydration."
        response = self.client.post("/analyze", json={"text": text, "retrieve_sources": True})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["analyzed_text"], text)
        self.assertEqual(body["decision_mode"], "evidence_only")
        self.assertFalse(body["classification_performed"])
        self.assertFalse(body["classifier_loaded"])
        for forbidden in ("model_score", "confidence", "predicted_class", "internal_label", "public_label", "decision_threshold"):
            self.assertNotIn(forbidden, body)
        self.evidence_mock.assert_called_once_with(text, requested=True, excluded_domain=None)

    def test_each_request_uses_its_supplied_text(self):
        first = "Unique first claim"
        second = "Different second claim"
        self.client.post("/analyze", json={"text": first, "retrieve_sources": True})
        self.client.post("/analyze", json={"text": second, "retrieve_sources": True})
        self.assertEqual([call.args[0] for call in self.evidence_mock.call_args_list], [first, second])

    def test_long_text_is_not_silently_truncated(self):
        text = ("Mahabang pahayag na susuriin. " * 1200).strip()
        response = self.client.post("/analyze", json={"text": text, "retrieve_sources": True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["analyzed_text"], text)
        self.assertEqual(self.evidence_mock.call_args.args[0], text)

    def test_empty_and_whitespace_inputs_are_rejected(self):
        for text in ("", "   \n\t"):
            response = self.client.post("/analyze", json={"text": text})
            self.assertEqual(response.status_code, 422)
            self.assertNotIn("assessment_label", response.json())

    def test_evidence_lookup_is_opt_in(self):
        self.client.post("/analyze", json={"text": "A claim"})
        self.evidence_mock.assert_called_once_with("A claim", requested=False, excluded_domain=None)

    def test_related_sources_endpoint_does_not_classify(self):
        response = self.client.post("/related-sources", json={"text": "A claim"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["classification_performed"])
        self.assertFalse(body["classifier_loaded"])
        self.assertNotIn("model_score", body)

    def test_published_fact_check_is_attributed(self):
        finding = {
            "assessment_status": "published_fact_check",
            "assessment_label": "Published fact-check: False",
            "assessment_basis": "Example Check published a closely matching ClaimReview rating.",
            "decision_source": "published_fact_check",
            "retrieval_status": "available",
            "related_sources": [],
            "fact_check_status": "available",
            "fact_check_matches": [{"url": "https://example.org/check", "publisher": "Example Check", "rating": "False"}],
        }
        self.evidence_mock.return_value = finding
        body = self.client.post("/analyze", json={"text": "Exact checked claim", "retrieve_sources": True}).json()
        self.assertEqual(body["assessment_label"], "Published fact-check: False")
        self.assertEqual(body["decision_source"], "published_fact_check")

    def test_context_uses_only_supplied_metadata(self):
        response = self.client.post("/analyze", json={
            "text": "Selected post caption",
            "context": {"author": "Example News", "published_text": "2h", "extraction_scope": "Facebook post caption"},
        })
        explanation = response.json()["context_explanation"]
        self.assertEqual(explanation["author"], "Example News")
        self.assertEqual(explanation["recency"], "Could not determine")
        self.assertEqual(explanation["checked_material"], "Facebook post caption")
        self.assertIn("No trained classifier", explanation["assessment_scope"])

    def test_image_text_reaches_evidence_contract(self):
        with patch.object(application, "extract_image_text", return_value={"extraction_status": "completed", "ocr_text": "OCR sample text"}):
            response = self.client.post("/analyze/image", files={"file": ("sample.png", io.BytesIO(b"png"), "image/png")})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["analyzed_text"], "OCR sample text")
        self.assertFalse(response.json()["classification_performed"])

    def test_media_failure_never_becomes_an_assessment(self):
        with patch.object(application, "extract_image_text", side_effect=MediaProcessingError("No readable text was found.")):
            response = self.client.post("/analyze/image", files={"file": ("sample.png", io.BytesIO(b"png"), "image/png")})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("assessment_label", response.json())

    def test_public_candidate_submission_is_retired(self):
        response = self.client.post("/candidates", json={"text": "A claim", "consent_to_store": True})
        self.assertEqual(response.status_code, 410)


if __name__ == "__main__":
    unittest.main()
