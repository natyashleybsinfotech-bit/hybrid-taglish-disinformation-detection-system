import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import model_runtime
import retrieval
import fact_check


class ModelRuntimeTests(unittest.TestCase):
    def test_missing_model_is_reported_as_unavailable(self):
        runtime = model_runtime.ModelRuntime("definitely-missing-artifacts")
        self.assertFalse(runtime.initialize()["ready"])
        with self.assertRaises(model_runtime.ModelUnavailableError):
            runtime.predict("Sample claim")

    def test_alternative_model_switch_is_rejected(self):
        for path in ("model_1.joblib", "model_2.joblib", "model_3.joblib", "hybrid_model.pkl"):
            with self.assertRaises(model_runtime.ModelUnavailableError):
                model_runtime.configure_model(path)

class RetrievalTests(unittest.TestCase):
    def test_search_query_removes_ui_text_and_blocks_social_sites(self):
        query = retrieval._search_query(
            "DOLE approves a wage increase. Read more https://facebook.com/example"
        )
        self.assertNotIn("Read more", query)
        self.assertNotIn("https://facebook.com/example", query)
        self.assertIn("-site:facebook.com", query)

    def test_missing_key_is_non_fatal(self):
        with patch.object(retrieval.config, "SERPER_API_KEY", ""):
            result = retrieval.retrieve_related_sources("sample")
        self.assertEqual(result["retrieval_status"], "unavailable_not_configured")
        self.assertEqual(result["related_sources"], [])


class FactCheckTests(unittest.TestCase):
    def test_missing_key_is_non_fatal(self):
        with patch.object(fact_check.config, "GOOGLE_FACT_CHECK_ENABLED", True), patch.object(
            fact_check.config, "GOOGLE_FACT_CHECK_API_KEY", ""
        ):
            result = fact_check.search_fact_checks("sample claim")
        self.assertEqual(result["status"], "unavailable_not_configured")

    def test_claim_review_link_and_rating_are_returned(self):
        payload = b'{"claims":[{"text":"The sample claim","claimant":"Example","claimReview":[{"publisher":{"name":"Example Fact Check","site":"example.org"},"url":"https://example.org/fact-check","title":"Fact check title","textualRating":"False"}]}]}'

        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *_args): return False
            def read(self, *_args): return payload

        with patch.object(fact_check.config, "GOOGLE_FACT_CHECK_ENABLED", True), patch.object(
            fact_check.config, "GOOGLE_FACT_CHECK_API_KEY", "test-key"
        ), patch.object(fact_check, "open_provider", return_value=FakeResponse()):
            result = fact_check.search_fact_checks("The sample claim")
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["matches"][0]["rating"], "False")
        self.assertEqual(result["matches"][0]["url"], "https://example.org/fact-check")
        self.assertIsNone(result["signal"])



if __name__ == "__main__":
    unittest.main()
