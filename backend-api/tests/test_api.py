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
    def test_evidence_cleanup_preserves_exact_model_input_and_text_checked(self):
        claim = 'The city opened three public schools in Manila on Monday.'
        original = claim + ' WATCH: https://example.com/999 Thank you very much.'
        self.retrieval_mock.return_value = {'retrieval_status': 'available', 'related_sources': [
            {'url': 'https://www.philstar.com/report', 'article_text': claim + ' Families attended the opening ceremony.'},
            {'url': 'https://tribune.net.ph/report', 'article_text': claim + ' The education office welcomed the development.'},
        ]}
        application.classify.return_value = Prediction(internal_label='Misleading', public_label='Potentially Misleading', confidence=.9, model_score=.9, predicted_class=1, model_status='ready', model_name='Test model', model_version='test-1')
        response = self.client.post('/analyze', json={'text': original, 'retrieve_sources': True})
        self.assertEqual(response.status_code, 200)
        value = response.json()
        self.assertEqual(value['analyzed_text'], original)
        application.classify.assert_called_once_with(original)
        self.assertEqual(value['model_public_label'], 'Potentially Misleading')
        self.assertEqual(value['final_label'], 'No Misleading Information Detected')

    def test_selected_video_caption_skips_media_and_has_exact_caption_provenance(self):
        caption="The city opened three schools in Manila on Monday."
        with patch.object(application,'process_video',side_effect=AssertionError('Caption only must not extract media')) as media:
            result=self.client.post('/analyze/video-caption',json={'text':caption,'page_url':'https://www.facebook.com/post/123','context':{'caption_complete':True,'extraction_scope':'Claimed whole video'}})
        self.assertEqual(result.status_code,200)
        body=result.json();self.assertEqual(body['analyzed_text'],caption)
        self.assertEqual(body['input_type'],'video');self.assertEqual(body['extraction_status'],'caption_only')
        self.assertEqual(body['context']['analysis_basis'],'video_caption_selected')
        self.assertEqual(body['context_explanation']['checked_material'],'Video post caption only')
        self.assertEqual(body['extraction']['transcript_status'],'not_requested')
        self.assertEqual(body['extraction']['transcript_text'],'');self.assertTrue(body['extraction']['caption_only'])
        self.assertFalse(body['extraction']['caption_fallback_used'])
        media.assert_not_called();application.classify.assert_called_once_with(caption)

    def test_unusable_or_incomplete_video_captions_never_produce_a_prediction(self):
        for text,context in [('',{}),('WATCH!',{}),('Watch now!',{}),('Panoorin!',{}),('https://example.com/a https://example.com/b',{}),('#Manila #News',{}),('Read full story in the comments.',{}),('Collapsed caption…',{}),('A complete public caption.',{'caption_complete':False})]:
            with self.subTest(text=text):
                result=self.client.post('/analyze/video-caption',json={'text':text,'context':context})
                self.assertEqual(result.status_code,422);self.assertNotIn('public_label',result.json())
        application.classify.assert_not_called();self.retrieval_mock.assert_not_called()

    def test_video_caption_outage_is_an_error_without_a_fabricated_prediction(self):
        application.classify.side_effect=application.ModelUnavailableError('Unavailable')
        result=self.client.post('/analyze/video-caption',json={'text':'The city opened three schools.'})
        self.assertEqual(result.status_code,503);self.assertNotIn('public_label',result.json())

    def test_video_quality_fallback_never_uses_a_bare_watch_prompt(self):
        with patch.object(application,'process_video',side_effect=application.SpeechQualityError('Unclear')):
            result=self.client.post('/extract/video',files={'file':('clip.mp4',b'video','video/mp4')},data={'post_text':'Watch now!'})
        self.assertEqual(result.status_code,422);application.classify.assert_not_called()


    def test_audio_provider_outage_does_not_turn_into_caption_prediction(self):
        for status,code in [('unavailable',503),('rate_limited',429)]:
            with patch.object(application,'process_video',side_effect=application.SpeechServiceError(status)):
                response=self.client.post('/extract/video',files={'file':('news.mp4',b'video','video/mp4')},data={'post_text':'A complete video caption.'})
            self.assertEqual(response.status_code,code)
            self.assertNotIn('public_label',response.json())
        application.classify.assert_not_called()

    def test_video_quality_failure_uses_only_complete_bound_caption(self):
        caption="The city opened three schools in Manila on Monday."
        for route in ['/extract/video','/analyze/video']:
            with patch.object(application,'process_video',side_effect=application.SpeechQualityError('Unclear speech')) as extract:
                response=self.client.post(route,files={'file':('news.mp4',b'complete-video','video/mp4')},data={'post_text':caption,'context_json':'{"caption_complete":true}','page_url':'https://www.facebook.com/post/123'})
            self.assertEqual(response.status_code,200)
            body=response.json();self.assertEqual(body['analyzed_text'],caption)
            self.assertEqual(body['extraction_status'],'caption_fallback')
            self.assertEqual(body['context_explanation']['checked_material'],'Video caption only')
            self.assertTrue(body['extraction']['caption_fallback_used'])
            self.assertEqual(body['extraction']['transcript_text'],'')
            self.assertNotIn('review_token',body)
            self.assertTrue(extract.call_args.kwargs['caption_fallback_allowed'])
            application.classify.assert_called_with(caption)

    def test_caption_fallback_never_masks_infrastructure_errors_or_incomplete_captions(self):
        for caption,context,error in [('', '{}',application.SpeechQualityError('Unclear speech')),('WATCH!','{}',application.SpeechQualityError('Unclear speech')),('Collapsed caption…','{}',application.SpeechQualityError('Unclear speech')),('A complete caption.','{"caption_complete":false}',application.SpeechQualityError('Unclear speech')),('A complete caption.','{}',application.MediaProcessingError('FFmpeg could not process the submitted video.'))]:
            with self.subTest(caption=caption,error=type(error).__name__),patch.object(application,'process_video',side_effect=error):
                response=self.client.post('/extract/video',files={'file':('news.mp4',b'video','video/mp4')},data={'post_text':caption,'context_json':context})
            self.assertEqual(response.status_code,422)
        application.classify.assert_not_called()




    def test_identical_article_url_aliases_merge_but_changed_bodies_are_retained(self):
        first={'url':'https://www.gmanetwork.com/news/report/','content_status':'readable','article_text':'The same complete article body.'}
        alias={**first,'url':'https://www.gmanetwork.com/news/report'}
        self.assertEqual(len(application._deduplicate_readable_sources([first,alias])),1)
        corrected={**alias,'article_text':'A different body explicitly corrects the earlier claim.'}
        self.assertEqual(len(application._deduplicate_readable_sources([first,corrected])),2)
        different={**first,'url':'https://www.gmanetwork.com/news/another-report/'}
        self.assertEqual(len(application._deduplicate_readable_sources([first,different])),2)

    def test_evidence_override_exports_passages_and_preserves_original_model(self):
        claim = 'The city opened three public schools in Manila on Monday.'
        self.retrieval_mock.return_value = {
            'retrieval_status': 'available', 'focused_used': False,
            'related_sources': [
                {'url': 'https://www.philstar.com/report', 'title': 'School opening',
                 'article_text': claim + ' Families attended the opening ceremony.'},
                {'url': 'https://tribune.net.ph/report', 'title': 'Three schools opened',
                 'article_text': claim + ' The education office welcomed the development.'},
            ],
        }
        application.classify.return_value = Prediction(
            internal_label='Misleading', public_label='Potentially Misleading',
            confidence=.9, model_score=.9, predicted_class=1,
            model_status='ready', model_name='Test model', model_version='test-1',
        )
        response = self.client.post('/analyze', json={'text': claim, 'retrieve_sources': True})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['final_label'], 'No Misleading Information Detected')
        self.assertEqual(body['model_public_label'], 'Potentially Misleading')
        self.assertEqual(body['model_score'], .9)
        self.assertIsNone(body['final_confidence'])
        self.assertEqual(body['verification_status'], 'evidence_assessed')
        self.assertTrue(all(s['evidence_excerpt'] == claim and s['used_for_decision'] for s in body['related_sources']))
        self.assertTrue(all('article_text' not in s for s in body['related_sources']))
        application.classify.assert_called_once()

    def test_trusted_article_link_from_post_is_checked_but_not_sufficient_alone(self):
        claim = "Scarlet Witch is returning in Avengers: Doomsday"
        url = "https://www.gmanetwork.com/news/lifestyle/hobbiesandactivities/1009209/scarlet-witch-is-returning-in-avengers-doomsday/story/"
        self.retrieval_mock.return_value = {
            "retrieval_status": "no_results",
            "related_sources": [],
            "focused_used": True,
        }
        self.inspection_mock.side_effect = lambda sources, _claim: [
            {
                **source,
                "title": "Scarlet Witch is returning in 'Avengers: Doomsday'",
                "source": "gmanetwork.com",
                "content_status": "readable",
                "article_text": (
                    "Elizabeth Olsen's Scarlet Witch is making a comeback in the Marvel Cinematic Universe. "
                    "In the post-credit scene of VisionQuest, Robert Downey Jr.'s Doctor Doom is seen digging "
                    "up Scarlet Witch. Other heroes making a comeback are Chris Evans, Chris Hemsworth, and "
                    "the original X-Men. The Wakandans, led by Shuri, are also joining Avengers: Doomsday."
                ),
            }
            for source in sources
        ]
        application.classify.return_value = Prediction(
            internal_label="Misleading",
            public_label="Potentially Misleading",
            confidence=1.0,
            model_status="ready",
            model_name="Test model",
            model_version="test-1",
        )

        response = self.client.post("/analyze", json={
            "text": claim,
            "retrieve_sources": True,
            "context": {"visible_links": [url]},
        })

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["public_label"], "Potentially Misleading")
        self.assertEqual(body["decision_source"], "screening_model")
        self.assertEqual(body["evidence_relationship"], "supports")
        self.assertEqual(body["related_sources"][0]["origin"], "post_link")
        self.assertEqual(body["related_sources"][0]["relationship"], "supports")
        self.assertEqual(body["evidence_urls"], [])

    def test_untrusted_or_non_https_post_links_are_not_fetched(self):
        response = self.client.post("/analyze", json={
            "text": "A complete claim to check.",
            "retrieve_sources": True,
            "context": {"visible_links": [
                "https://example.invalid/story",
                "http://www.gmanetwork.com/news/story",
            ]},
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["related_sources"], [])
        self.assertEqual(self.inspection_mock.call_args.args[0], [])

    def test_unreadable_first_article_gets_one_focused_retry(self):
        blocked = {'url': 'https://philstar.com/blocked', 'title': 'Original result'}
        readable = {'url': 'https://gmanetwork.com/report', 'title': 'Readable report', 'content_status': 'readable',
                    'article_text': 'The city opened three public schools in Manila on Monday.'}
        self.retrieval_mock.side_effect = [
            {'retrieval_status': 'available', 'related_sources': [blocked]},
            {'retrieval_status': 'available', 'related_sources': [readable]},
        ]
        self.inspection_mock.side_effect = [[dict(blocked, content_status='inaccessible')], [readable]]
        response = self.client.post('/analyze', json={'text': 'The city opened three public schools in Manila on Monday.', 'retrieve_sources': True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['related_sources'][0]['url'], readable['url'])
        self.assertEqual(self.retrieval_mock.call_count, 2)
        self.assertTrue(self.retrieval_mock.call_args.kwargs['focused'])
        self.assertEqual(self.retrieval_mock.call_args.kwargs['excluded_urls'], (blocked['url'],))
        application.classify.assert_called_once()

    def test_failed_focused_retry_preserves_labeled_search_preview(self):
        blocked = {
            'url': 'https://philstar.com/blocked',
            'title': 'Search result title',
            'snippet': 'Search result snippet',
            'search_title': 'Search result title',
            'search_snippet': 'Search result snippet',
            'content_status': 'inaccessible',
        }
        self.retrieval_mock.side_effect = [{'retrieval_status': 'available', 'related_sources': [blocked]}, RuntimeError('provider down')]
        response = self.client.post('/related-sources', json={'text': 'A supplied complete claim'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['retrieval_status'], 'available')
        self.assertEqual(len(response.json()['related_sources']), 1)
        source = response.json()['related_sources'][0]
        self.assertEqual(source['content_status'], 'inaccessible')
        self.assertEqual(source['search_title'], 'Search result title')
        self.assertEqual(source['search_snippet'], 'Search result snippet')
        self.assertEqual(source['relationship'], 'unverified')
        self.assertFalse(response.json()['classification_performed'])
        application.classify.assert_not_called()

    def test_readable_and_search_only_sources_are_distinguished(self):
        readable = {'url': 'https://philstar.com/report', 'content_status': 'readable', 'title': 'Matched article'}
        inaccessible = {
            'url': 'https://inquirer.net/unknown-story',
            'content_status': 'inaccessible',
            'search_title': 'Search result title',
            'search_snippet': 'Search result snippet',
        }
        self.retrieval_mock.return_value = {'retrieval_status': 'available', 'related_sources': [readable, inaccessible]}
        response = self.client.post('/related-sources', json={'text': 'The complete supplied news claim'})
        self.assertEqual(response.status_code, 200)
        sources = response.json()['related_sources']
        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0]['url'], readable['url'])
        self.assertEqual(sources[1]['url'], inaccessible['url'])
        self.assertEqual(sources[1]['content_status'], 'inaccessible')
        self.assertEqual(sources[1]['search_title'], 'Search result title')
        self.assertEqual(sources[0]['relationship'], 'unverified')
        self.assertEqual(sources[0]['relationship_reason'], 'The full article could not be assessed.')
        self.assertEqual(sources[1]['relationship'], 'unverified')
        application.classify.assert_not_called()

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(application.app)

    def setUp(self):
        self.screening_mode_patcher = patch.object(application.config, "SCREENING_MODE", "model")
        self.screening_mode_patcher.start()
        self.model_patcher = patch.object(
            application,
            "classify",
            return_value=Prediction(
                internal_label="Non-Misleading",
                public_label="No Misleading Information Detected",
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
        self.retrieval_mock = self.retrieval_patcher.start()
        self.inspection_patcher = patch.object(application, "inspect_related_sources", side_effect=lambda sources, _claim: [dict(source, content_status=source.get('content_status', 'readable')) for source in sources])
        self.inspection_mock = self.inspection_patcher.start()
        self.fact_check_patcher = patch.object(
            application,
            "search_fact_checks",
            return_value={"status": "no_results", "matches": [], "signal": None},
        )
        self.fact_check_mock = self.fact_check_patcher.start()
        self.candidate_patcher = patch.object(application.database, "create_candidate", return_value=42)
        self.candidate_mock = self.candidate_patcher.start()
        self.audit_patcher = patch.object(application.database, "log_audit", return_value=1)
        self.audit_patcher.start()
        self.decision_patcher = patch.object(application.database, "save_screening_decision", return_value=77)
        self.decision_mock = self.decision_patcher.start()

    def tearDown(self):
        self.screening_mode_patcher.stop()
        self.model_patcher.stop()
        self.retrieval_patcher.stop()
        self.inspection_patcher.stop()
        self.fact_check_patcher.stop()
        self.candidate_patcher.stop()
        self.audit_patcher.stop()
        self.decision_patcher.stop()

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

    def test_two_related_sources_cannot_override_the_model(self):
        self.retrieval_mock.return_value = {
            "retrieval_status": "available",
            "related_sources": [
                {"title": "Agency confirms supplied claim", "url": "https://one.example/report", "source": "one.example"},
                {"title": "Supplied claim confirmed", "url": "https://two.example/report", "source": "two.example"},
            ],
        }
        self.fact_check_mock.return_value = {
            "status": "available",
            "matches": [],
            "signal": None,
        }
        response = self.client.post("/analyze", json={"retrieve_sources": True, "text": "A supplied claim"})
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["public_label"], "No Misleading Information Detected")
        self.assertEqual(body["retrieval_status"], "available")
        self.assertEqual(body["fact_check_status"], "not_assessed")
        self.assertEqual(len(body["related_sources"]), 2)
        self.assertEqual(body["fact_check_matches"], [])
        self.assertEqual(body["decision_source"], "screening_model")
        self.assertEqual(body["evidence_relationship"], "unverified")
        self.assertFalse(body["evidence_adjusted"])
        self.retrieval_mock.assert_called_once()
        self.fact_check_mock.assert_not_called()

    def test_readable_article_assertions_change_final_not_original_model(self):
        claim = "The Bureau of Customs destroyed 3174 boxes of illicit vape products worth 1.4 billion pesos in Navotas."
        application.classify.return_value = Prediction(
            internal_label="Misleading", public_label="Potentially Misleading", confidence=.8,
            model_status="ready", model_name="Test model", model_version="test-1",
            model_score=.8, predicted_class=1,
        )
        self.retrieval_mock.return_value = {"retrieval_status": "available", "related_sources": [
            {"url": "https://www.philstar.com/report"}, {"url": "https://tribune.net.ph/report"},
        ]}
        self.inspection_mock.side_effect = lambda sources, _claim: [
            {**sources[0], "content_status": "readable", "title": "Publisher A report", "article_text": claim + " The agency supervised disposal."},
            {**sources[1], "content_status": "readable", "title": "Publisher B report", "article_text": claim + " Officials confirmed the action."},
        ]
        response = self.client.post("/analyze", json={"text": claim, "retrieve_sources": True})
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["model_public_label"], "Potentially Misleading")
        self.assertEqual(body["model_score"], .8)
        self.assertEqual(body["model_confidence"], .8)
        self.assertIsNone(body["confidence"])
        self.assertEqual(body["final_label"], "No Misleading Information Detected")
        self.assertEqual(body["public_label"], "No Misleading Information Detected")
        self.assertTrue(body["evidence_adjusted"])
        self.assertEqual(body["decision_source"], "verified_evidence")
        self.assertEqual(body["verification_status"], "evidence_assessed")
        self.assertNotIn("article_text", body["related_sources"][0])

    def test_primary_cdc_direct_health_support_can_override_model_through_api(self):
        claim = "Drinking enough water helps prevent dehydration."
        application.classify.return_value = Prediction(
            internal_label="Misleading", public_label="Potentially Misleading", confidence=.87,
            model_status="ready", model_name="Test model", model_version="test-1",
            model_score=.87, predicted_class=1,
        )
        self.retrieval_mock.return_value = {
            "retrieval_status": "available",
            "related_sources": [{
                "url": "https://www.cdc.gov/healthy-weight-growth/water-healthy-drinks/",
                "source": "cdc.gov",
            }],
        }
        self.inspection_mock.side_effect = lambda sources, _claim: [{
            **sources[0],
            "content_status": "readable",
            "article_text": "Drinking water can prevent dehydration, which may cause unclear thinking.",
        }]

        response = self.client.post("/analyze", json={"text": claim, "retrieve_sources": True})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["model_public_label"], "Potentially Misleading")
        self.assertEqual(body["public_label"], "No Misleading Information Detected")
        self.assertEqual(body["evidence_relationship"], "supports")
        self.assertEqual(body["decision_source"], "verified_evidence")
        self.assertEqual(body["verification_status"], "evidence_assessed")
        self.assertEqual(body["evidence_rule"], "scoped_primary_authority")
        self.assertEqual(body["model_score"], .87)
        self.assertTrue(body["related_sources"][0]["used_for_decision"])
        self.assertTrue(body["related_sources"][0]["evidence_excerpt"])

    def test_claim_mismatch_scenarios_stay_unverified_through_api(self):
        scenarios = {
            "official_other_event": [{"title": "Official update on another event", "url": "https://doh.gov.ph/other"}],
            "same_names_different_event": [{"title": "Mayor Santos at a different meeting", "url": "https://one.example/a"}],
            "wrong_date_location": [{"title": "Cebu report from a different date", "url": "https://one.example/b"}],
            "contradictory_quantity": [{"title": "12 people injured, not 21", "url": "https://one.example/c"}],
            "negation": [{"title": "Agency did not approve the plan", "url": "https://one.example/d"}],
            "repeated_report": [{"title": "Wire report", "url": "https://one.example/e"}, {"title": "Wire report", "url": "https://two.example/e"}],
            "conflicting_reports": [{"title": "Plan approved", "url": "https://one.example/f"}, {"title": "Plan denied", "url": "https://two.example/f"}],
        }
        for name, sources in scenarios.items():
            with self.subTest(name=name):
                self.retrieval_mock.return_value = {"retrieval_status": "available", "related_sources": sources}
                body = self.client.post("/analyze", json={"text": "A complete short claim", "retrieve_sources": True}).json()
                self.assertEqual(body["public_label"], body["model_public_label"])
                self.assertEqual(body["predicted_class"], body["model_predicted_class"])
                self.assertEqual(body["decision_source"], "screening_model")
                self.assertEqual(body["evidence_relationship"], "unverified")
                self.assertFalse(body["evidence_adjusted"])

    def test_source_lookup_endpoint_does_not_run_classification(self):
        self.retrieval_mock.return_value = {
            "retrieval_status": "available",
            "related_sources": [{"title": "Related report", "url": "https://example.org/report"}],
        }
        application.classify.reset_mock()
        response = self.client.post("/related-sources", json={"text": "A supplied claim"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["retrieval_status"], "available")
        self.assertFalse(response.json()["classification_performed"])
        application.classify.assert_not_called()
        self.retrieval_mock.assert_any_call("A supplied claim", excluded_domain=None)
        self.assertLessEqual(self.retrieval_mock.call_count, 2)

    def test_empty_source_lookup_does_not_run_classification_or_retrieval(self):
        application.classify.reset_mock()
        response = self.client.post("/related-sources", json={"text": "  \n\t "})
        self.assertEqual(response.status_code, 422)
        application.classify.assert_not_called()
        self.retrieval_mock.assert_not_called()

    def test_lookup_is_opt_in(self):
        response = self.client.post("/analyze", json={"text": "A supplied claim", "retrieve_sources": False})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["retrieval_status"], "not_requested")
        self.assertEqual(response.json()["fact_check_status"], "not_requested")
        self.retrieval_mock.assert_not_called()
        self.fact_check_mock.assert_not_called()

    def test_evidence_only_mode_skips_classifier_and_uses_requested_reliable_sources(self):
        claim = "Drinking enough water helps prevent dehydration."
        self.screening_mode_patcher.stop()
        with patch.object(application.config, "SCREENING_MODE", "evidence_only"):
            self.retrieval_mock.return_value = {"retrieval_status": "available", "related_sources": [{
                "url": "https://www.philstar.com/health/article",
                "source": "philstar.com",
            }]}
            self.inspection_mock.side_effect = lambda sources, _claim: [{
                **sources[0], "content_status": "readable",
                "article_text": "Drinking water can prevent dehydration.",
            }]
            application.classify.reset_mock()

            response = self.client.post("/analyze", json={
                "text": claim, "retrieve_sources": True,
            })

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["screening_mode"], "evidence_only")
        self.assertEqual(body["decision_source"], "evidence_review")
        self.assertIn(body["public_label"], ("No Misleading Information Detected", "Potentially Misleading"))
        self.assertEqual(body["verification_status"], "not_verified")
        self.assertEqual(body["evidence_relationship"], "supports")
        self.assertIsNone(body["model_score"])
        self.assertIsNone(body["model_public_label"])
        application.classify.assert_not_called()
        self.retrieval_mock.assert_any_call(claim, excluded_domain=None)

    def test_evidence_only_mode_marks_missing_support_unverified_without_a_model(self):
        self.screening_mode_patcher.stop()
        with patch.object(application.config, "SCREENING_MODE", "evidence_only"):
            application.classify.reset_mock()
            response = self.client.post("/analyze", json={
                "text": "A complete claim with no source support.", "retrieve_sources": False,
            })

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["screening_mode"], "evidence_only")
        self.assertEqual(body["public_label"], "Potentially Misleading")
        self.assertEqual(body["decision_source"], "evidence_review")
        self.assertEqual(body["verification_status"], "not_verified")
        self.assertIsNone(body["final_predicted_class"])
        self.assertIsNone(body["model_score"])
        self.assertIn("not a factual verdict", body["decision_basis"])
        application.classify.assert_not_called()
        self.retrieval_mock.assert_not_called()

    def test_evidence_only_startup_does_not_initialize_the_classifier(self):
        self.screening_mode_patcher.stop()
        with patch.object(application.config, "SCREENING_MODE", "evidence_only"), patch.object(
            application.database, "migrate", return_value={"status": "not_configured"}
        ), patch.object(
            application.database, "database_health", return_value={"status": "not_configured"}
        ), patch.object(application, "initialize_model", side_effect=AssertionError("classifier must remain off")) as initialize:
            with TestClient(application.app) as client:
                health = client.get("/health")
                ready = client.get("/ready")

        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["screening_mode"], "evidence_only")
        self.assertEqual(health.json()["model_status"], "disabled")
        self.assertEqual(ready.status_code, 503)
        self.assertFalse(ready.json()["ready"])
        self.assertEqual(ready.json()["database"]["status"], "not_configured")
        initialize.assert_not_called()

    def test_both_model_labels_are_explicitly_unverified_without_claim_evidence(self):
        for internal, public, value, predicted in (
            ("Non-Misleading", "No Misleading Information Detected", .1, 0),
            ("Misleading", "Potentially Misleading", .9, 1),
        ):
            application.classify.return_value = Prediction(internal_label=internal, public_label=public,
                confidence=.9, model_status="ready", model_name="Test model", model_version="test-1",
                model_score=value, predicted_class=predicted)
            self.retrieval_mock.return_value = {"retrieval_status": "no_results", "related_sources": []}
            result = self.client.post("/analyze", json={"text": "A complete statement for screening.", "retrieve_sources": True}).json()
            self.assertEqual(result["public_label"], public)
            self.assertEqual(result["verification_status"], "not_verified")
            self.assertEqual(result["evidence_urls"], [])
            self.assertFalse(result["evidence_adjusted"])

    def test_uncertain_video_speech_never_reaches_classifier(self):
        application.classify.reset_mock()
        with patch.object(application, "process_video", side_effect=MediaProcessingError("Some speech could not be transcribed clearly. No prediction was made from the uncertain transcript.")):
            response = self.client.post("/extract/video", files={"file": ("unclear.mp4", b"video-fixture", "video/mp4")})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("public_label", response.json())
        application.classify.assert_not_called()

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
            "Potentially Misleading", "No Misleading Information Detected"
        })
        self.assertIn("out-of-distribution", first.json()["model_scope_notice"])
        self.candidate_mock.assert_not_called()

    def test_public_screening_does_not_use_lexical_fact_check_as_a_verdict(self):
        self.fact_check_mock.return_value = {
            "status": "available",
            "matches": [{
                "title": "Published review", "url": "https://example.org/fact-check",
                "publisher": "Example Check", "rating": "False",
                "match_strength": .9, "matched_term_count": 4,
            }],
            "signal": None,
        }
        response = self.client.post("/analyze", json={"text": "A closely matching claim", "retrieve_sources": True})
        body = response.json()
        self.assertEqual(body["public_label"], "No Misleading Information Detected")
        self.assertEqual(body["decision_source"], "screening_model")
        self.assertEqual(body["fact_check_status"], "not_assessed")
        self.assertEqual(body["fact_check_matches"], [])
        self.assertFalse(body["evidence_adjusted"])
        self.fact_check_mock.assert_not_called()

    def test_incomplete_facebook_caption_is_rejected_before_classification(self):
        application.classify.reset_mock()
        response = self.client.post("/analyze", json={"text": "HINDI KAILANGANG I-CONFINE...", "context": {"extraction_scope": "Facebook post caption", "caption_complete": False}})
        self.assertEqual(response.status_code, 422)
        self.assertIn("incomplete", response.json()["detail"])
        application.classify.assert_not_called()

    def test_short_complete_facebook_claim_is_screened(self):
        response = self.client.post("/analyze", json={"text": "May bagyo ngayon.", "context": {"extraction_scope": "Facebook post caption", "caption_complete": True}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["decision_source"], "screening_model")

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
        self.assertIn("relative Facebook label", explanation["recency_explanation"])
        self.assertEqual(explanation["separate_statements"], [])
        self.assertIn("Individual claims were not fact-checked", explanation["assessment_scope"])
        self.assertEqual(explanation["checked_material"], "Post text and readable image text")

    def test_unrelated_fetched_articles_leave_no_available_source_status(self):
        self.retrieval_mock.return_value = {
            "retrieval_status": "available", "related_sources": [{"url": "https://gmanetwork.com/news/report"}],
        }
        self.inspection_mock.side_effect = None
        self.inspection_mock.return_value = []
        for endpoint, payload in (
            ("/analyze", {"text": "A complete claim to check.", "retrieve_sources": True}),
            ("/related-sources", {"text": "A complete claim to check."}),
        ):
            with self.subTest(endpoint=endpoint):
                response = self.client.post(endpoint, json=payload)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["retrieval_status"], "no_results")
                self.assertEqual(response.json()["related_sources"], [])

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

    def test_post_context_uses_only_reliable_metadata_and_filtered_links(self):
        explanation = application._context_explanation("Selected post caption", {
            "author": "Example News",
            "published_at": "2026-10-22T06:00:00+08:00",
            "published_text": "2h",
            "original_post_url": "https://www.facebook.com/example/posts/123",
            "visible_links": ["https://example.org/report", "javascript:alert(1)", "https://example.org/report"],
            "extraction_scope": "Selected Facebook text",
        })
        self.assertEqual(explanation["author"], "Example News")
        self.assertTrue(explanation["recency"].startswith("Posted about "))
        self.assertEqual(explanation["original_post_url"], "https://www.facebook.com/example/posts/123")
        self.assertEqual(explanation["relevant_links"], ["https://example.org/report"])
        self.assertEqual(explanation["checked_material"], "Selected Facebook text")
        ambiguous = application._context_explanation("Selected post caption", {"published_text": "2h"})
        self.assertEqual(ambiguous["timing"], "2h")
        self.assertEqual(ambiguous["recency"], "Posted about 2 hours ago")

    def test_image_text_reaches_same_screening_contract(self):
        extraction = {"extraction_status": "completed", "ocr_text": "OCR sample text"}
        with patch.object(application, "extract_image_text", return_value=extraction):
            response = self.client.post(
                "/analyze/image", files={"file": ("sample.png", io.BytesIO(b"png"), "image/png")},
                data={"post_text": "An unrelated caption from an older extension"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["input_type"], "image")
        self.assertEqual(response.json()["analyzed_text"], "An unrelated caption from an older extension OCR sample text")
        self.assertEqual(response.json()["extraction"]["caption_text"], "An unrelated caption from an older extension")
        self.assertEqual(response.json()["context_explanation"]["checked_material"], "Facebook post caption and image OCR")
        self.assertIn("context_explanation", response.json())
        self.assertIn(response.json()["public_label"], {
            "Potentially Misleading", "No Misleading Information Detected"
        })
        self.candidate_mock.assert_not_called()

    def test_evidence_only_image_keeps_caption_ocr_and_retrieves_sources_without_classifier(self):
        self.screening_mode_patcher.stop()
        with patch.object(application.config, "SCREENING_MODE", "evidence_only"), patch.object(
            application, "extract_image_text",
            return_value={"extraction_status": "completed", "ocr_text": "Image headline"},
        ):
            application.classify.reset_mock()
            response = self.client.post(
                "/analyze/image",
                files={"file": ("sample.png", io.BytesIO(b"png"), "image/png")},
                data={
                    "post_text": "Caption says the city opened a school.",
                    "retrieve_sources": "true",
                },
            )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["analyzed_text"], "Caption says the city opened a school. Image headline")
        self.assertEqual(body["extraction"]["caption_text"], "Caption says the city opened a school.")
        self.assertEqual(body["extraction"]["ocr_text"], "Image headline")
        self.assertEqual(body["screening_mode"], "evidence_only")
        self.assertEqual(body["retrieval_status"], "disabled")
        self.retrieval_mock.assert_called_once_with(
            "Caption says the city opened a school. Image headline", excluded_domain=None,
        )
        application.classify.assert_not_called()

    def test_multiple_post_images_are_ocr_read_before_one_image_screening(self):
        extracts = [
            {"extraction_status": "completed", "ocr_text": "First image headline", "discarded_ocr_detections": 1},
            {"extraction_status": "completed", "ocr_text": "Second image detail", "discarded_ocr_detections": 2},
        ]
        with patch.object(application, "extract_image_text", side_effect=extracts) as ocr:
            response = self.client.post("/analyze/images", files=[
                ("files", ("one.png", b"one", "image/png")),
                ("files", ("two.png", b"two", "image/png")),
            ])
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["input_type"], "image")
        self.assertEqual(body["analyzed_text"], "First image headline Second image detail")
        self.assertEqual(body["extraction"]["ocr_by_image"], ["First image headline", "Second image detail"])
        self.assertEqual(body["extraction"]["discarded_ocr_detections"], 3)
        self.assertEqual(body["extraction"]["caption_text"], "")
        self.assertEqual(ocr.call_count, 2)
        application.classify.assert_called_once()

    def test_identical_image_text_is_screened_once_but_each_image_is_traced(self):
        item = {"extraction_status": "completed", "ocr_text": "Same image claim"}
        with patch.object(application, "extract_image_text", side_effect=[item, item]):
            response = self.client.post("/analyze/images", files=[
                ("files", ("one.png", b"one", "image/png")),
                ("files", ("two.png", b"two", "image/png")),
            ])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["analyzed_text"], "Same image claim")
        self.assertEqual(response.json()["extraction"]["ocr_by_image"],
                         ["Same image claim", "Same image claim"])
        application.classify.assert_called_once()

    def test_multiple_post_images_fail_without_a_partial_prediction(self):
        with patch.object(application, "extract_image_text", side_effect=[
            {"extraction_status": "completed", "ocr_text": "First image"},
            MediaProcessingError("No readable text was found in the image."),
        ]):
            response = self.client.post("/analyze/images", files=[
                ("files", ("one.png", b"one", "image/png")),
                ("files", ("two.png", b"two", "image/png")),
            ])
        self.assertEqual(response.status_code, 422)
        self.assertIn("Image 2", response.json()["detail"])
        application.classify.assert_not_called()

    def test_video_text_reaches_same_screening_contract(self):
        extraction = {
            "extraction_status": "completed", "analyzed_text": "Transcript\nFrame text",
            "transcript_text": "Transcript", "frame_ocr_text": "Frame text", "sampled_frames": 1,
            "speech_frame_agreement": "review_required",
        }
        with patch.object(application, "process_video", return_value=extraction):
            preview = self.client.post(
                "/extract/video", files={"file": ("sample.mp4", io.BytesIO(b"video"), "video/mp4")},
                data={"post_text": "An unrelated caption from an older extension"},
            )
        self.assertTrue(preview.json()["review_required"])
        self.assertEqual(preview.json()["post_text"], "An unrelated caption from an older extension")
        self.assertEqual(preview.json()["extraction"]["speech_frame_agreement"], "review_required")
        application.classify.assert_not_called()
        response = self.client.post("/analyze/confirmed-video", json={
            "review_token": preview.json()["review_token"], "confirmed": True,
            "transcript_text": "Transcript", "frame_ocr_text": "Frame text",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["input_type"], "video")
        self.assertEqual(response.json()["analyzed_text"], "An unrelated caption from an older extension Transcript Frame text")
        self.assertIn("context_explanation", response.json())
        self.assertEqual(response.json()["context_explanation"]["checked_material"], "Facebook post caption, video audio transcript, video-frame OCR")
        self.assertEqual(response.json()["extraction"]["caption_text"], "An unrelated caption from an older extension")
        self.assertEqual(response.json()["extraction"]["sampled_frames"], 1)
        self.candidate_mock.assert_not_called()

    def test_evidence_only_video_keeps_caption_and_retrieves_after_user_confirms_extraction(self):
        self.screening_mode_patcher.stop()
        extraction = {
            "extraction_status": "completed", "analyzed_text": "Transcript",
            "transcript_text": "Transcript", "frame_ocr_text": "", "sampled_frames": 0,
            "speech_frame_agreement": "not_checked",
        }
        with patch.object(application.config, "SCREENING_MODE", "evidence_only"), patch.object(
            application, "process_video", return_value=extraction
        ):
            application.classify.reset_mock()
            preview = self.client.post(
                "/extract/video",
                files={"file": ("sample.mp4", io.BytesIO(b"video"), "video/mp4")},
                data={"post_text": "Video post caption.", "retrieve_sources": "true"},
            )
            response = self.client.post("/analyze/confirmed-video", json={
                "review_token": preview.json()["review_token"], "confirmed": True,
                "transcript_text": "Transcript", "frame_ocr_text": "",
            })

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["analyzed_text"], "Video post caption. Transcript")
        self.assertEqual(body["extraction"]["caption_text"], "Video post caption.")
        self.assertEqual(body["screening_mode"], "evidence_only")
        self.assertEqual(body["retrieval_status"], "disabled")
        self.retrieval_mock.assert_called_once_with(
            "Video post caption. Transcript", excluded_domain=None,
        )
        application.classify.assert_not_called()

    def test_unrelated_frame_text_is_not_screened_with_speech(self):
        extraction = {
            "extraction_status": "completed", "analyzed_text": "Spoken claim",
            "transcript_text": "Spoken claim", "frame_ocr_text": "Unrelated on-screen story",
            "frame_ocr_included": False, "sampled_frames": 1,
            "speech_frame_agreement": "review_required",
        }
        with patch.object(application, "process_video", return_value=extraction):
            preview = self.client.post("/extract/video", files={
                "file": ("sample.mp4", io.BytesIO(b"video"), "video/mp4")})
        self.assertFalse(preview.json()["extraction"]["frame_ocr_included"])
        response = self.client.post("/analyze/confirmed-video", json={
            "review_token": preview.json()["review_token"], "confirmed": True,
            "transcript_text": "Spoken claim", "frame_ocr_text": "Unrelated on-screen story",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["analyzed_text"], "Spoken claim")
        self.assertEqual(response.json()["extraction"]["frame_ocr_text"], "Unrelated on-screen story")
        self.assertFalse(response.json()["extraction"]["frame_ocr_included"])
        self.assertEqual(response.json()["context_explanation"]["checked_material"], "video audio transcript")

    def test_media_failure_never_becomes_success(self):
        with patch.object(
            application, "extract_image_text", side_effect=MediaProcessingError("No readable text was found.")
        ):
            response = self.client.post(
                "/analyze/image", files={"file": ("sample.png", io.BytesIO(b"png"), "image/png")}
            )
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("public_label", response.json())

    def test_video_keeps_speech_and_frames_without_an_older_client_caption(self):
        extraction = {"extraction_status": "completed", "analyzed_text": "Spoken sentence.\nVisible frame text.",
            "transcript_text": "Spoken sentence.", "frame_ocr_text": "Visible frame text.", "sampled_frames": 2,
            "transcript_status": "completed", "discarded_ocr_detections": 1,
            "transcript_segments": [{"start_seconds": 1, "end_seconds": 3, "text": "Spoken sentence."}]}
        with patch.object(application, "process_video", return_value=extraction):
            preview = self.client.post("/extract/video", data={"post_text": "Public caption."},
                files={"file": ("sample.mp4", b"video", "video/mp4")})
        response = self.client.post("/analyze/confirmed-video", json={
            "review_token": preview.json()["review_token"], "confirmed": True,
            "transcript_text": "Spoken sentence.", "frame_ocr_text": "Visible frame text.",
        })
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["extraction"]["caption_text"], "Public caption.")
        self.assertEqual(body["extraction"]["transcript_text"], "Spoken sentence.")
        self.assertEqual(body["extraction"]["frame_ocr_text"], "Visible frame text.")
        self.assertEqual(body["extraction"]["discarded_ocr_detections"], 1)
        self.assertEqual(body["analyzed_text"], "Public caption. Spoken sentence. Visible frame text.")

    def test_video_review_cannot_be_skipped_reused_or_changed(self):
        extraction = {"extraction_status": "completed", "analyzed_text": "Spoken sentence.",
                      "transcript_text": "Spoken sentence.", "frame_ocr_text": "", "sampled_frames": 0}
        with patch.object(application, "process_video", return_value=extraction):
            preview = self.client.post("/extract/video", files={"file": ("sample.mp4", b"video", "video/mp4")})
        token = preview.json()["review_token"]
        application.classify.reset_mock()
        mismatched = self.client.post("/analyze/confirmed-video", json={
            "review_token": token, "confirmed": True,
            "transcript_text": "Different sentence.", "frame_ocr_text": "",
        })
        self.assertEqual(mismatched.status_code, 409)
        application.classify.assert_not_called()
        replay = self.client.post("/analyze/confirmed-video", json={
            "review_token": token, "confirmed": True,
            "transcript_text": "Spoken sentence.", "frame_ocr_text": "",
        })
        self.assertEqual(replay.status_code, 409)
        application.classify.assert_not_called()

    def test_direct_video_analysis_returns_screening_result_without_manual_review(self):
        extraction = {
            "extraction_status": "completed",
            "analyzed_text": "Words spoken in the video.",
            "transcript_text": "Words spoken in the video.",
            "frame_ocr_text": "",
            "sampled_frames": 2,
            "transcript_status": "completed",
        }
        with patch.object(application, "process_video", return_value=extraction):
            response = self.client.post(
                "/analyze/video",
                data={"post_text": "A complete Facebook caption."},
                files={"file": ("sample.mp4", b"video", "video/mp4")},
            )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["input_type"], "video")
        self.assertEqual(body["analyzed_text"], "A complete Facebook caption. Words spoken in the video.")
        self.assertEqual(body["extraction"]["caption_text"], "A complete Facebook caption.")
        self.assertEqual(body["extraction"]["transcript_text"], "Words spoken in the video.")
        self.assertFalse(body["extraction"]["review_confirmed"])
        self.assertEqual(body["context_explanation"]["checked_material"], "Facebook post caption, video audio transcript")
        application.classify.assert_called_once()

    def test_direct_video_analysis_requires_review_when_speech_and_frames_disagree(self):
        extraction = {
            "extraction_status": "completed",
            "analyzed_text": "Words spoken in the video.",
            "transcript_text": "Words spoken in the video.",
            "frame_ocr_text": "Different headline on screen.",
            "frame_ocr_included": False,
            "speech_frame_agreement": "review_required",
            "sampled_frames": 1,
        }
        application.classify.reset_mock()
        with patch.object(application, "process_video", return_value=extraction):
            preview = self.client.post(
                "/analyze/video",
                data={"post_text": "A complete Facebook caption.", "retrieve_sources": "true"},
                files={"file": ("sample.mp4", b"video-fixture", "video/mp4")},
            )

        self.assertEqual(preview.status_code, 200)
        body = preview.json()
        self.assertTrue(body["review_required"])
        self.assertEqual(body["extraction"]["speech_frame_agreement"], "review_required")
        self.assertNotIn("public_label", body)
        application.classify.assert_not_called()

        confirmed = self.client.post("/analyze/confirmed-video", json={
            "review_token": body["review_token"],
            "confirmed": True,
            "transcript_text": extraction["transcript_text"],
            "frame_ocr_text": extraction["frame_ocr_text"],
        })
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.json()["extraction"]["review_confirmed"], True)
        application.classify.assert_called_once()

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


    def test_candidate_model_authoritative_keeps_classifier_label_and_skips_llm(self):
        self.retrieval_mock.return_value = {"retrieval_status":"available", "related_sources":[{
            "url":"https://www.gmanetwork.com/news/report", "title":"Related report",
            "content_status":"readable", "article_text":"A related news report."}]}
        for label in ["Misleading", "Non-Misleading"]:
            application.classify.return_value = Prediction(
                internal_label=label,
                public_label="Potentially Misleading" if label == "Misleading" else "No Misleading Information Detected",
                confidence=.9, model_status="ready", model_name="Fine-tuned DistilBERT + LR",
                model_version="candidate-test", predicted_class=int(label == "Misleading"),
                model_score=.9 if label == "Misleading" else .1)
            with patch.object(application.config,"MODEL_AUTHORITATIVE",True), patch.object(application,"apply_evidence",side_effect=AssertionError("No evidence override")):
                response=self.client.post('/analyze',json={"text":"A complete supplied claim.","retrieve_sources":True})
            self.assertEqual(response.status_code,200)
            body=response.json()
            self.assertEqual(body['internal_label'],label)
            self.assertEqual(body['decision_source'],'screening_model')
            self.assertFalse(body['evidence_adjusted'])
            self.assertEqual(body['supporting_source_count'],0)

    def test_candidate_model_outage_does_not_call_llm_fallback(self):
        application.classify.side_effect=application.ModelUnavailableError('candidate unavailable')
        with patch.object(application.config,"MODEL_AUTHORITATIVE",True):
            response=self.client.post('/analyze',json={"text":"A complete supplied claim.","retrieve_sources":True})
        self.assertEqual(response.status_code,503)
        self.assertNotIn('public_label',response.json())



if __name__ == "__main__":
    unittest.main()
