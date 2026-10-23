import os
import sys
import unittest
import io
import json
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
    def test_search_query_preserves_authored_control_like_text_and_blocks_social_sites(self):
        query = retrieval._search_query(
            "A witness wrote See less in the caption. https://facebook.com/example"
        )
        self.assertIn("See less", query)
        self.assertNotIn("https://facebook.com/example", query)
        self.assertIn("-site:facebook.com", query)

    def test_missing_key_is_non_fatal(self):
        with patch.object(retrieval.config, "SERPER_API_KEY", ""):
            result = retrieval.retrieve_related_sources("sample")
        self.assertEqual(result["retrieval_status"], "unavailable_not_configured")
        self.assertEqual(result["related_sources"], [])

    def test_credible_but_unrelated_result_is_rejected(self):
        payload = {
            "organic": [{
                "title": "Compliance filing in a separate court case",
                "link": "https://sc.judiciary.gov.ph/example.pdf",
                "snippet": "The order was issued in October after the parties filed pleadings.",
            }]
        }
        with patch.object(retrieval.config, "SERPER_ENABLED", True), patch.object(
            retrieval.config, "SERPER_API_KEY", "fixture-not-live"
        ), patch.object(retrieval, "open_provider", return_value=io.BytesIO(json.dumps(payload).encode())):
            result = retrieval.retrieve_related_sources(
                "Batasan Hills Quezon police naaresto ang suspek matapos ang murder"
            )
        self.assertEqual(result["retrieval_status"], "no_results")
        self.assertEqual(result["related_sources"], [])

    def test_short_query_requires_all_informative_terms(self):
        payload = {
            "organic": [{
                "title": "Police publish an unrelated traffic advisory",
                "link": "https://pia.gov.ph/traffic-advisory",
                "snippet": "Motorists should expect road closures.",
            }]
        }
        with patch.object(retrieval.config, "SERPER_ENABLED", True), patch.object(
            retrieval.config, "SERPER_API_KEY", "fixture-not-live"
        ), patch.object(retrieval, "open_provider", return_value=io.BytesIO(json.dumps(payload).encode())):
            result = retrieval.retrieve_related_sources("Quezon police")
        self.assertEqual(result["retrieval_status"], "no_results")

    def test_generic_snippet_overlap_cannot_replace_event_title_match(self):
        payload = {"organic": [{
            "title": "Police arrest suspects in viral pickpocketing video",
            "link": "https://abs-cbn.com/unrelated-pickpocketing",
            "snippet": "A hot pursuit operation passed Quezon Avenue and Batasan Tunnel.",
        }]}
        with patch.object(retrieval.config, "SERPER_ENABLED", True), patch.object(
            retrieval.config, "SERPER_API_KEY", "fixture-not-live"
        ), patch.object(retrieval, "open_provider", return_value=io.BytesIO(json.dumps(payload).encode())):
            result = retrieval.retrieve_related_sources(
                "Batasan Hills Quezon police hot pursuit operation"
            )
        self.assertEqual(result["retrieval_status"], "no_results")

    def test_related_results_are_ranked_by_matching_post_terms(self):
        payload = {
            "organic": [
                {
                    "title": "Quezon police issue suspect advisory",
                    "link": "https://pia.gov.ph/quezon-advisory",
                    "snippet": "General information for residents.",
                },
                {
                    "title": "3 killed in QC shooting; suspect arrested",
                    "link": "https://mb.com.ph/batasan-shooting",
                    "snippet": "Police arrested a 38-year-old man after a shooting in Barangay Batasan Hills.",
                },
            ]
        }
        with patch.object(retrieval.config, "SERPER_ENABLED", True), patch.object(
            retrieval.config, "SERPER_API_KEY", "fixture-not-live"
        ), patch.object(retrieval, "open_provider", return_value=io.BytesIO(json.dumps(payload).encode())):
            result = retrieval.retrieve_related_sources(
                "Batasan Hills Quezon police arrested a 38-year-old suspect after a shooting"
            )
        self.assertEqual(result["retrieval_status"], "available")
        self.assertEqual([source["url"] for source in result["related_sources"]], [
            "https://mb.com.ph/batasan-shooting",
            "https://pia.gov.ph/quezon-advisory",
        ])

    def test_focused_retry_recovers_related_approved_result(self):
        first_payload = {"organic": [{
            "title": "Compliance filing in a separate court case",
            "link": "https://sc.judiciary.gov.ph/example.pdf",
            "snippet": "An unrelated order issued in October.",
        }]}
        focused_payload = {"organic": [{
            "title": "3 killed in QC shooting; suspect arrested",
            "link": "https://mb.com.ph/batasan-shooting",
            "snippet": "Police arrested a suspect after a shooting in Barangay Batasan Hills.",
        }]}
        responses = [
            io.BytesIO(json.dumps(first_payload).encode()),
            io.BytesIO(json.dumps(focused_payload).encode()),
        ]
        with patch.object(retrieval.config, "SERPER_ENABLED", True), patch.object(
            retrieval.config, "SERPER_API_KEY", "fixture-not-live"
        ), patch.object(retrieval, "open_provider", side_effect=responses) as provider:
            result = retrieval.retrieve_related_sources(
                "Batasan Hills Quezon police naaresto ang suspek matapos ang murder"
            )
        self.assertEqual(result["retrieval_status"], "available")
        self.assertEqual(result["related_sources"][0]["url"], "https://mb.com.ph/batasan-shooting")
        self.assertEqual(provider.call_count, 2)

    def test_fictional_episode_is_rejected_despite_surname_and_verb_overlap(self):
        payload = {"organic": [{
            "title": "Juan dela Cruz: Kael, patuloy na hinanap ang vigilante | Episode 21",
            "link": "https://www.abs-cbn.com/entertainment/studios/tv/2026/10/22/juan-dela-cruz-episode-21",
            "snippet": "Panoorin ang paboritong Kapamilya teleserye episode.",
        }]}
        query = (
            "TO THE RESCUE SI NANAY: Nanay Kara Dela Cruz said that PSSg Tyran John "
            "Miranda patuloy na tumulong sa pamilya matapos ang insidente."
        )
        with patch.object(retrieval.config, "SERPER_ENABLED", True), patch.object(
            retrieval.config, "SERPER_API_KEY", "fixture-not-live"
        ), patch.object(retrieval, "open_provider", side_effect=[
            io.BytesIO(json.dumps(payload).encode()), io.BytesIO(json.dumps(payload).encode())
        ]):
            result = retrieval.retrieve_related_sources(query)
        self.assertEqual(result["retrieval_status"], "no_results")
        self.assertEqual(result["related_sources"], [])

    def test_relevant_news_video_with_full_person_entity_is_allowed(self):
        payload = {"organic": [{
            "title": "Kara Dela Cruz thanks PSSg Tyran John Miranda after rescue",
            "link": "https://www.gmanetwork.com/news/video/rescue-interview/",
            "snippet": "Kara Dela Cruz described how the police officer helped her family.",
        }]}
        query = "Nanay Kara Dela Cruz thanked PSSg Tyran John Miranda after the rescue."
        with patch.object(retrieval.config, "SERPER_ENABLED", True), patch.object(
            retrieval.config, "SERPER_API_KEY", "fixture-not-live"
        ), patch.object(retrieval, "open_provider", return_value=io.BytesIO(json.dumps(payload).encode())):
            result = retrieval.retrieve_related_sources(query)
        self.assertEqual(result["retrieval_status"], "available")
        self.assertEqual(result["related_sources"][0]["url"], payload["organic"][0]["link"])


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
