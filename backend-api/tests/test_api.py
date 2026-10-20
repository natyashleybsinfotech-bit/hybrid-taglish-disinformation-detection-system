import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fastapi.testclient import TestClient

import app as application
from media_processing import MediaProcessingError
from model_runtime import Prediction, ModelRuntime


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(application.app)

    def setUp(self):
        self.model_patcher = patch.object(
            application,
            "classify",
            return_value=Prediction(
                internal_label="Non-Misleading",
                public_label="Prediction: Non-Misleading",
                confidence=0.84,
                model_status="ready",
                model_name="Test model",
                model_version="test-1",
            ),
        )
        self.model_patcher.start()
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
        self.candidate_patcher = patch.object(application.database, "create_candidate", return_value=42)
        self.candidate_mock = self.candidate_patcher.start()
        self.audit_patcher = patch.object(application.database, "log_audit", return_value=1)
        self.audit_patcher.start()

    def tearDown(self):
        self.model_patcher.stop()
        self.retrieval_patcher.stop()
        self.fact_check_patcher.stop()
        self.candidate_patcher.stop()
        self.audit_patcher.stop()

    def test_health_is_available_when_database_is_offline(self):
        with patch.object(application.database, "database_health", return_value={
            "status": "unavailable", "engine": "sqlite"
        }):
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["database"]["status"], "unavailable")

    def test_readiness_fails_when_model_is_unavailable(self):
        with patch.object(application, "model_health", return_value={"status": "unavailable"}):
            response = self.client.get("/ready")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["ready"])

    def test_empty_inputs_are_rejected_without_prediction(self):
        for text in ("", " \n\t "):
            response = self.client.post("/analyze", json={"text": text})
            self.assertEqual(response.status_code, 422)
            self.assertNotIn("public_label", response.json())

    def test_inference_failure_returns_503_without_a_prediction(self):
        with patch.object(application, "classify", side_effect=application.ModelUnavailableError("encoder unavailable")):
            response = self.client.post("/analyze", json={"text": "Fresh supplied text"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("model_score", response.json())
        self.assertIn("unavailable", response.json()["detail"])

    def test_failed_artifact_load_keeps_health_reachable_and_prediction_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = ModelRuntime(directory)
            with patch.object(application, "initialize_model", missing.initialize), patch.object(
                application, "model_health", missing.health
            ), patch.object(application, "classify", missing.predict), patch.object(
                application.database, "migrate", return_value={"status": "not_configured"}
            ), patch.object(application.config, "APP_ENV", "development"):
                with TestClient(application.app) as client:
                    self.assertEqual(client.get("/health").status_code, 200)
                    self.assertEqual(client.get("/ready").status_code, 503)
                    response = client.post("/analyze", json={"text": "Fresh claim"})
                    self.assertEqual(response.status_code, 503)
                    self.assertIn("unavailable", response.json()["detail"])
                    self.assertNotIn("model_score", response.json())

    def test_retrieval_failure_does_not_change_classification(self):
        baseline = self.client.post("/analyze", json={"retrieve_sources": True, "text": "A supplied claim"}).json()
        with patch.object(application, "retrieve_related_sources", side_effect=RuntimeError("network unavailable")):
            response = self.client.post("/analyze", json={"retrieve_sources": True, "text": "A supplied claim"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["model_score"], baseline["model_score"])
        self.assertEqual(response.json()["internal_label"], baseline["internal_label"])
        self.assertEqual(response.json()["retrieval_status"], "unavailable")

    def test_long_text_is_passed_completely_to_classifier(self):
        text = "Taglish test input. " * 2000 + "TAIL_MARKER"
        self.client.post("/analyze", json={"text": text})
        application.classify.assert_called_once_with(text)

    def test_model_activation_cannot_change_the_pinned_classifier(self):
        with patch.object(application.database, "activate_model_version") as activate:
            with self.assertRaises(application.HTTPException) as error:
                application.admin_activate_model(99, "admin")
            self.assertEqual(error.exception.status_code, 410)
            activate.assert_not_called()

    def test_training_version_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            application.RetrainingRequest(dataset_version_id=1, requested_version_name="../../outside")

    def test_production_startup_fails_on_migration_error(self):
        with patch.object(application.config, "APP_ENV", "production"), patch.object(
            application.config, "validate_runtime_config"
        ), patch.object(application.database, "migrate", return_value={"status": "unavailable"}):
            with self.assertRaisesRegex(RuntimeError, "migration failed"):
                with TestClient(application.app):
                    pass

    def test_production_startup_does_not_hide_bootstrap_errors(self):
        with patch.object(application.config, "APP_ENV", "production"), patch.object(
            application.config, "validate_runtime_config"
        ), patch.object(application.database, "migrate", return_value={"status": "available"}), patch.object(
            application.database, "get_active_model", return_value=None
        ), patch.object(application.database, "ensure_bootstrap_admin", side_effect=RuntimeError("bootstrap failure")):
            with self.assertRaisesRegex(RuntimeError, "bootstrap failure"):
                with TestClient(application.app):
                    pass

    def test_disabled_training_does_not_queue_a_job(self):
        with patch.object(application.config, "TRAINING_ENABLED", False), patch.object(
            application.database, "queue_training_run"
        ) as queue:
            with self.assertRaises(application.HTTPException) as error:
                application.admin_queue_training(
                    application.RetrainingRequest(dataset_version_id=1, requested_version_name="test-v1"), "admin"
                )
            self.assertEqual(error.exception.status_code, 410)
            queue.assert_not_called()

    def test_text_contract_uses_deployable_model_fields(self):
        payload = {"text": "Isang test claim."}
        first = self.client.post("/analyze", json=payload)
        second = self.client.post("/analyze", json=payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["internal_label"], second.json()["internal_label"])
        self.assertEqual(first.json()["confidence"], second.json()["confidence"])
        self.assertEqual(first.json()["model_status"], "ready")
        self.assertEqual(first.json()["model_version"], "test-1")
        self.assertIsNone(first.json()["candidate_sample_id"])
        self.assertIn(first.json()["topic_suggestion"]["topic"], application.config.TOPIC_CATEGORIES)
        self.assertEqual(first.json()["evidence_status"], "not_captured")
        self.assertIn("context_explanation", first.json())
        self.assertIn("fact_check_matches", first.json())
        self.assertEqual(first.json()["page_url"], None)
        self.assertIn(first.json()["public_label"], {
            "Prediction: Misleading", "Prediction: Non-Misleading"
        })
        self.candidate_mock.assert_not_called()

    def test_google_fact_check_cannot_overwrite_public_verdict(self):
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
        self.assertEqual(body["public_label"], "Prediction: Non-Misleading")
        self.assertEqual(body["decision_source"], "screening_model")
        self.assertIsNone(body["decision_basis"])
        self.assertEqual(body["fact_check_status"], "admin_review_only")

    def test_context_does_not_fabricate_individual_fact_checks(self):
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
        self.assertIn("not been independently verified", explanation["recency_explanation"])
        self.assertEqual(explanation["separate_statements"], [])
        self.assertIn("Individual claims were not fact-checked", explanation["assessment_scope"])
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
            "Prediction: Misleading", "Prediction: Non-Misleading"
        })
        self.candidate_mock.assert_not_called()

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
        self.candidate_mock.assert_not_called()

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
        self.assertNotIn("token", login.json())
        with patch.object(application.config, "SESSION_SECRET", "test-session-secret"):
            status = self.client.get("/admin-api/system-status")
        self.assertEqual(status.status_code, 200)

    def test_afp_viewer_can_read_quality_status_but_not_govern_dataset(self):
        self.client.cookies.clear()
        with patch.object(application.config, "SESSION_SECRET", "test-session-secret"):
            token = application._create_token("afp-evaluator", "viewer")
            headers = {"Authorization": f"Bearer {token}"}
            status = self.client.get("/admin-api/system-status", headers=headers)
            candidates = self.client.get("/admin-api/candidates", headers=headers)
        self.assertEqual(status.status_code, 200)
        self.assertEqual(candidates.status_code, 403)
        self.assertEqual(candidates.json()["detail"], "This account has view-only access.")

    def test_admin_can_import_validated_csv_dataset(self):
        csv_data = (
            'text,label,topic,evidence_url,claim_group_id\n'
            '"Validated claim",Non-Misleading,"Other and General",https://example.com/evidence,claim-1\n'
        )
        with patch.object(application.config, "SESSION_SECRET", "test-session-secret"):
            token = application._create_token("admin", "admin")
            headers = {"Authorization": f"Bearer {token}"}
            with patch.object(application.database, "import_validated_dataset", return_value={
                "dataset_version_id": 7, "imported": 1,
                "partitions": {"train": 1, "validation": 0, "test": 0},
            }) as importer:
                response = self.client.post(
                    "/admin-api/dataset-versions/import",
                    headers=headers,
                    data={"version_name": "validated-v1"},
                    files={"file": ("validated.csv", csv_data, "text/csv")},
                )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["imported"], 1)
        self.assertEqual(importer.call_args.args[0], "validated-v1")

    def test_admin_can_bulk_add_approved_candidates(self):
        result = {
            "added": 8, "skipped_existing": 0, "skipped_missing_claim_group": 0,
            "partitions": {"train": 6, "validation": 1, "test": 1},
        }
        with patch.object(application.config, "SESSION_SECRET", "test-session-secret"):
            token = application._create_token("admin", "admin")
            headers = {"Authorization": f"Bearer {token}"}
            with patch.object(application.database, "bulk_add_approved_candidates", return_value=result):
                response = self.client.post(
                    "/admin-api/dataset-versions/4/items/bulk", headers=headers
                )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["partitions"]["train"], 6)


if __name__ == "__main__":
    unittest.main()
