import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import evidence_runtime


class EvidenceRuntimeTests(unittest.TestCase):
    def test_no_lookup_abstains(self):
        result = evidence_runtime.assess_evidence("A claim", requested=False)
        self.assertEqual(result["assessment_status"], "unresolved")
        self.assertEqual(result["decision_source"], "insufficient_evidence")

    def test_related_articles_do_not_become_truth_verdict(self):
        with patch.object(evidence_runtime, "retrieve_related_sources", return_value={
            "retrieval_status": "available", "related_sources": [{"title": "Related", "url": "https://news.example/story"}]
        }), patch.object(evidence_runtime, "search_fact_checks", return_value={"status": "no_results", "matches": []}):
            result = evidence_runtime.assess_evidence("A claim", requested=True)
        self.assertEqual(result["assessment_status"], "related_coverage")
        self.assertEqual(result["assessment_label"], "Related coverage found")
        self.assertNotIn("true", result["assessment_label"].lower())
        self.assertNotIn("false", result["assessment_label"].lower())

    def test_weak_fact_check_match_is_not_used_as_a_verdict(self):
        with patch.object(evidence_runtime, "retrieve_related_sources", return_value={"retrieval_status": "no_results", "related_sources": []}), patch.object(
            evidence_runtime, "search_fact_checks", return_value={"status": "available", "matches": [{
                "title": "Different claim", "url": "https://check.example/item", "publisher": "Check", "rating": "False",
                "match_strength": 0.69, "matched_term_count": 8,
            }]}
        ):
            result = evidence_runtime.assess_evidence("A claim", requested=True)
        self.assertEqual(result["assessment_status"], "unresolved")

    def test_strong_claimreview_surfaces_publisher_rating(self):
        match = {
            "title": "Exact claim", "url": "https://check.example/item", "publisher": "Check", "rating": "False",
            "match_strength": 0.91, "matched_term_count": 6,
        }
        with patch.object(evidence_runtime, "retrieve_related_sources", return_value={"retrieval_status": "no_results", "related_sources": []}), patch.object(
            evidence_runtime, "search_fact_checks", return_value={"status": "available", "matches": [match]}
        ):
            result = evidence_runtime.assess_evidence("Exact claim", requested=True)
        self.assertEqual(result["assessment_status"], "published_fact_check")
        self.assertEqual(result["assessment_label"], "Published fact-check: False")
        self.assertIn("publisher's finding", result["assessment_basis"])

    def test_provider_failures_return_unavailable_without_verdict(self):
        with patch.object(evidence_runtime, "retrieve_related_sources", side_effect=RuntimeError("down")), patch.object(
            evidence_runtime, "search_fact_checks", side_effect=RuntimeError("down")
        ):
            result = evidence_runtime.assess_evidence("A claim", requested=True)
        self.assertEqual(result["assessment_status"], "providers_unavailable")
        self.assertEqual(result["decision_source"], "insufficient_evidence")


if __name__ == "__main__":
    unittest.main()
