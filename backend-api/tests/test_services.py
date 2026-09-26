import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import mock_classifier
import retrieval
import fact_check


class MockClassifierTests(unittest.TestCase):
    def test_prediction_is_deterministic_and_paper_aligned(self):
        first = mock_classifier.classify("Sample Taglish claim para sa prototype")
        second = mock_classifier.classify("Sample Taglish claim para sa prototype")
        self.assertEqual(first, second)
        self.assertIn(first.internal_label, {"Misleading", "Non-Misleading"})
        self.assertIn(first.public_label, {
            "Potentially Misleading", "No Misleading Information Detected"
        })
        self.assertEqual(first.model_status, "mock-prototype")

    def test_empty_text_is_rejected(self):
        with self.assertRaises(ValueError):
            mock_classifier.classify("   ")


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
            def read(self): return payload

        with patch.object(fact_check.config, "GOOGLE_FACT_CHECK_ENABLED", True), patch.object(
            fact_check.config, "GOOGLE_FACT_CHECK_API_KEY", "test-key"
        ), patch.object(fact_check.request, "urlopen", return_value=FakeResponse()):
            result = fact_check.search_fact_checks("The sample claim")
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["matches"][0]["rating"], "False")
        self.assertEqual(result["matches"][0]["url"], "https://example.org/fact-check")
        self.assertEqual(result["signal"]["internal_label"], "Misleading")
        self.assertEqual(result["signal"]["source_url"], "https://example.org/fact-check")

    def test_weak_match_does_not_change_the_verdict(self):
        matches = [{
            "claim": "An unrelated claim",
            "rating": "False",
            "url": "https://example.org/unrelated",
            "match_strength": 0.2,
        }]
        self.assertIsNone(fact_check._evidence_signal(matches))


if __name__ == "__main__":
    unittest.main()
