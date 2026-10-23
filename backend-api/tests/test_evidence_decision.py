import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from evidence_decision import apply_evidence


MODEL_NO = {"internal_label": "Non-Misleading", "public_label": "No Misleading Information Detected"}
MODEL_YES = {"internal_label": "Misleading", "public_label": "Potentially Misleading"}


class EvidenceDecisionTests(unittest.TestCase):
    def test_no_evidence_falls_back_to_model(self):
        result = apply_evidence(MODEL_YES, [], [])
        self.assertEqual(result["public_label"], "Potentially Misleading")
        self.assertEqual(result["decision_source"], "screening_model")

    def test_one_related_source_does_not_override(self):
        result = apply_evidence(MODEL_YES, [{"title": "Related report", "url": "https://one.example"}], [])
        self.assertEqual(result["public_label"], "Potentially Misleading")
        self.assertEqual(result["decision_source"], "screening_model")

    def test_two_independent_filtered_sources_corroborate(self):
        sources = [
            {"title": "Agency confirms event", "url": "https://one.example"},
            {"title": "Event reported by officials", "url": "https://two.example"},
        ]
        result = apply_evidence(MODEL_YES, sources, [])
        self.assertEqual(result["public_label"], "No Misleading Information Detected")
        self.assertEqual(result["decision_source"], "corroborated_sources")

    def test_one_relevant_official_primary_source_corroborates(self):
        sources = [{"title": "Official seizure report", "url": "https://customs.gov.ph/report", "source": "customs.gov.ph"}]
        result = apply_evidence(MODEL_YES, sources, [])
        self.assertEqual(result["public_label"], "No Misleading Information Detected")
        self.assertEqual(result["decision_source"], "official_primary_source")

    def test_debunk_headlines_do_not_count_as_support(self):
        sources = [
            {"title": "Fact check: false claim spreads", "url": "https://one.example"},
            {"title": "Report debunks fake post", "url": "https://two.example"},
        ]
        result = apply_evidence(MODEL_NO, sources, [])
        self.assertEqual(result["decision_source"], "screening_model")

    def test_strong_false_fact_check_has_priority(self):
        match = {"url": "https://check.example", "publisher": "Check", "rating": "False", "match_strength": .9, "matched_term_count": 5}
        result = apply_evidence(MODEL_NO, [], [match])
        self.assertEqual(result["public_label"], "Potentially Misleading")
        self.assertEqual(result["decision_source"], "published_fact_check")

    def test_weak_fact_check_does_not_override(self):
        match = {"url": "https://check.example", "publisher": "Check", "rating": "False", "match_strength": .69, "matched_term_count": 5}
        result = apply_evidence(MODEL_NO, [], [match])
        self.assertEqual(result["public_label"], "No Misleading Information Detected")
        self.assertEqual(result["decision_source"], "screening_model")


if __name__ == "__main__":
    unittest.main()
