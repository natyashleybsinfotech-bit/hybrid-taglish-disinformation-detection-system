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
    def test_focused_query_keeps_action_amount_and_surface_words(self):
        claim = ('BREAKING NEWS: The Bureau of Customs destroyed P1.4 billion worth of smuggled '
                 'vape products. Watch the video and follow this page for updates. '
                 'Officials spoke at length while the public waited for details about the ceremony.')
        focused = retrieval._focused_search_query(claim)
        self.assertIn('destroyed', focused)
        self.assertIn('P1.4 billion', focused)
        self.assertIn('smuggled vape products', focused)
        self.assertNotIn('Watch', focused)
        self.assertTrue(retrieval._prefer_focused_first(claim))
        self.assertFalse(retrieval._prefer_focused_first('BOC destroys P1.4 billion smuggled vape products.'))

    def test_focused_query_keeps_person_suffix_with_action(self):
        claim = ('President Ferdinand Marcos Jr. created the National AI Council and adopted an AI '
                 'governance framework. Watch the full video and follow this page for updates. '
                 'More details and links will be shared with readers later today.')
        focused = retrieval._focused_search_query(claim)
        self.assertIn('Marcos Jr', focused)
        self.assertIn('created', focused)
        self.assertIn('adopted', focused)

    def test_focused_query_can_find_material_sentence_after_long_intro(self):
        intro = ('Watch our page for updates and share this story with friends. ' * 11)
        claim = intro + 'BOC destroyed P1.4 billion worth of smuggled vape products.'
        self.assertNotIn('BOC', retrieval._search_query(claim))
        focused = retrieval._focused_search_query(claim)
        self.assertIn('BOC destroyed P1.4 billion', focused)

    def test_long_caption_uses_compact_query_then_keeps_raw_fallback(self):
        claim = ('BREAKING NEWS: The Bureau of Customs destroyed P1.4 billion worth of smuggled '
                 'vape products. Watch the video for the complete story, follow this page for '
                 'updates, and share with your friends. Officials discussed the shipment at '
                 'length while the public waited for details about the ceremony.')
        first = {'organic': [{'title': 'BOC destroys P1.4 billion smuggled vape products',
                              'snippet': 'The Bureau of Customs destroyed smuggled vape products.',
                              'link': 'https://www.philstar.com/boc-vape'}]}
        second = {'organic': [{'title': 'Bureau of Customs destroys P1.4 billion smuggled vape products',
                               'snippet': 'Officials destroyed the illicit vape shipment.',
                               'link': 'https://tribune.net.ph/boc-vape'}]}
        with patch.object(retrieval.config, 'SERPER_ENABLED', True), patch.object(
            retrieval.config, 'SERPER_API_KEY', 'fixture-not-live'
        ), patch.object(retrieval, '_serper_search', side_effect=[first, second]) as search:
            result = retrieval.retrieve_related_sources(claim)
        self.assertEqual(search.call_args_list[0].args[0], retrieval._focused_search_query(claim))
        self.assertEqual(search.call_args_list[1].args[0], retrieval._search_query(claim))
        self.assertEqual(len(result['related_sources']), 2)

    def test_headline_verb_inflection_finds_same_event_without_relaxing_subject(self):
        claim = 'The council approves a new education plan.'
        matching = {'title': 'Council approved new education plan',
                    'snippet': 'The council approved the education plan after review.',
                    'link': 'https://www.philstar.com/education-plan'}
        unrelated = {'title': 'Council approved new transport plan',
                     'snippet': 'The council approved transport changes after review.',
                     'link': 'https://www.philstar.com/transport-plan'}
        self.assertTrue(retrieval._is_relevant(matching, retrieval._informative_terms(claim), claim)[0])
        self.assertFalse(retrieval._is_relevant(unrelated, retrieval._informative_terms(claim), claim)[0])

    def test_local_result_does_not_hide_direct_international_health_article(self):
        payload = {'organic': [
            {'title': 'Can water prevent dehydration?',
             'snippet': 'Local discussion asks whether water prevents dehydration.',
             'link': 'https://www.philstar.com/water-question'},
            {'title': 'Water can prevent dehydration',
             'snippet': 'Drinking water can prevent dehydration.',
             'link': 'https://www.cdc.gov/water-guidance'},
        ]}
        with patch.object(retrieval.config, 'SERPER_ENABLED', True), patch.object(
            retrieval.config, 'SERPER_API_KEY', 'fixture-not-live'
        ), patch.object(retrieval, 'open_provider', return_value=io.BytesIO(json.dumps(payload).encode())):
            result = retrieval.retrieve_related_sources('Water prevents dehydration.')
        self.assertEqual({item['url'] for item in result['related_sources']},
                         {'https://www.philstar.com/water-question', 'https://www.cdc.gov/water-guidance'})

    def test_short_claim_requires_the_specific_subject_not_only_generic_topic(self):
        claim = 'Drinking enough water helps prevent dehydration.'
        generic = {'title': 'Drinking-water', 'snippet': 'Drinking water can prevent infections from unsafe water.', 'link': 'https://who.int/water'}
        specific = {'title': 'About Water and Healthier Drinks', 'snippet': 'Drinking water can prevent dehydration.', 'link': 'https://cdc.gov/water'}
        self.assertFalse(retrieval._is_relevant(generic, retrieval._informative_terms(claim), claim)[0])
        self.assertTrue(retrieval._is_relevant(specific, retrieval._informative_terms(claim), claim)[0])

    def test_noisy_media_caption_matches_current_article_and_rejects_old_event(self):
        claim = 'pholo PIA MRT-3, planong isapribado sa 2027 October 22, 2026 NEWS'
        current = {
            'title': 'MRT-3, target maisapribado sa 2027',
            'snippet': 'Target ng Department of Transportation (DOTr) na maisapribado ang operasyon ng Metro Rail Transit Line 3 (MRT-3) sa kalagitnaan ng 2027.',
            'link': 'https://www.philstar.com/pilipino-star-ngayon/metro/2026/10/24/2565360/mrt-3-target-maisapribado-sa-2027',
        }
        historical = {
            'title': 'Pagtaas ng pasahe sa MRT-3, hindi maiiwasan – DOTr',
            'snippet': 'Kasunod ng pangamba na matutuloy ang planong isapribado ang operasyon at maintenance nito.',
            'link': 'https://www.philstar.com/pilipino-star-ngayon/metro/2022/11/10/2222671/pagtaas-ng-pasahe-sa-mrt-3-hindi-maiiwasan-dotr',
        }

        results = retrieval._relevant_sources(
            {'organic': [historical, current]},
            retrieval._informative_terms(claim),
            claim,
            None,
        )

        self.assertEqual([source['url'] for _score, source in results], [current['link']])

    def test_search_query_removes_media_metadata_but_keeps_claim_and_event_year(self):
        query = retrieval._search_query(
            'pholo PIA MRT-3, planong isapribado sa 2027 October 22, 2026 NEWS'
        )

        self.assertIn('MRT-3', query)
        self.assertIn('2027', query)
        self.assertIn('target', query.casefold())
        self.assertIn('maisapribado', query.casefold())
        self.assertNotIn('pholo', query.casefold())
        self.assertNotIn('pia', query.casefold())
        self.assertNotIn('2026', query)
        self.assertNotIn('news', query.casefold())

    def test_focused_retry_excludes_unreadable_url_before_publisher_ranking(self):
        claim = 'Customs seized illicit vape products in Navotas'
        first = {'title': 'Customs seized illicit vape products in Navotas', 'snippet': claim, 'link': 'https://philstar.com/blocked'}
        second = dict(first, link='https://philstar.com/readable')
        with patch.object(retrieval.config, 'SERPER_ENABLED', True), patch.object(retrieval.config, 'SERPER_API_KEY', 'fixture'), patch.object(retrieval, '_serper_search', return_value={'organic': [first, second]}) as provider:
            result = retrieval.retrieve_related_sources(claim, focused=True, excluded_urls=(first['link'],))
        self.assertEqual([s['url'] for s in result['related_sources']], [second['link']])
        provider.assert_called_once()

    def test_named_public_health_sources_are_allowed_without_lookalike_hosts(self):
        for host in ('www.cdc.gov', 'www.nhs.uk', 'www.who.int'):
            self.assertTrue(retrieval._is_trusted_domain(host))
        for host in ('cdc.gov.example.org', 'nhs.uk.example.org', 'fakecdc.gov'):
            self.assertFalse(retrieval._is_trusted_domain(host))

    def test_andasian_esports_report_is_eligible_for_related_sources(self):
        claim = "VALORANT announced Manila to host the first ever VCT Pacific Cup 2027"
        article = {
            "title": "VALORANT announced Manila to host first-ever VCT Pacific Cup 2027",
            "snippet": "Riot Games announced that Manila will host the inaugural VCT Pacific Cup from 29 April to 23 May 2027.",
            "link": "https://andasian.com/valorant-announced-manila-to-host-first-ever-vct-pacific-cup-2027/",
        }

        rows = retrieval._relevant_sources(
            {"organic": [article]}, retrieval._informative_terms(claim), claim, None
        )

        self.assertEqual([source["url"] for _score, source in rows], [article["link"]])
        self.assertTrue(retrieval._is_trusted_domain("www.andasian.com"))
        self.assertFalse(retrieval._is_trusted_domain("andasian.com.example.org"))

    def test_related_event_without_claimed_host_city_is_rejected(self):
        claim = "VALORANT announced Manila to host the first ever VCT Pacific Cup 2027"
        article = {
            "title": "Riot Games unveils VCT Pacific partnered teams for 2027",
            "snippet": "VALORANT Champions Tour (VCT) Pacific 2027 has unveiled eight organizations.",
            "link": "https://technology.inquirer.net/149981/riot-games-unveils-vct-pacific-partnered-teams-for-2027",
        }

        self.assertFalse(
            retrieval._is_relevant(article, retrieval._informative_terms(claim), claim)[0]
        )

    def test_generic_doj_page_and_unrelated_drug_snippet_do_not_match_abortion_post(self):
        claim = (
            "Babalà, sensitibo ang paksa. Bukas ang Department of Justice (DOJ) na luwagan "
            "ang batas laban sa abortion para sa mga biktima ng panggagahasa at iba pang "
            "medical cases sa ilalim ng panukalang reporma sa criminal law ng bansa. "
            "AB*RTION BAN LUWAGAN SA GINAHASA – DOJ"
        )
        unrelated = {
            "title": "News Articles :: Department of Justice - Republic of the Philippines",
            "snippet": (
                "The Department of Justice (DOJ) secured the conviction of a Thai national "
                "for importing dangerous drugs into the Philippines, in violation of Section 4."
            ),
            "link": "https://www.doj.gov.ph/news-articles.html",
        }

        self.assertEqual(
            retrieval._relevant_sources(
                {"organic": [unrelated]},
                retrieval._informative_terms(claim),
                claim,
                None,
            ),
            [],
        )

    def test_specific_article_title_with_three_claim_terms_remains_relevant(self):
        claim = (
            "Babalà, sensitibo ang paksa. Bukas ang Department of Justice (DOJ) na luwagan "
            "ang batas laban sa abortion para sa mga biktima ng panggagahasa at iba pang "
            "medical cases sa ilalim ng panukalang reporma sa criminal law ng bansa."
        )
        relevant = {
            "title": "DOJ considers easing abortion ban for rape victims",
            "snippet": "The proposal concerns criminal-law reform and medical cases.",
            "link": "https://www.gmanetwork.com/news/story",
        }

        self.assertTrue(
            retrieval._is_relevant(
                relevant, retrieval._informative_terms(claim), claim
            )[0]
        )

    def test_multiple_independent_local_and_international_publishers_are_eligible(self):
        claim = "Quezon police arrested suspect after shooting Batasan Hills"
        items = [
            {"title": claim, "snippet": claim, "link": f"https://{host}/story"}
            for host in (
                "manilastandard.net",
                "businessmirror.com.ph",
                "apnews.com",
                "unlisted.example",
            )
        ]

        rows = retrieval._relevant_sources(
            {"organic": items}, retrieval._informative_terms(claim), claim, None
        )

        self.assertEqual(
            {row["url"].split("/")[2] for _score, row in rows},
            {"manilastandard.net", "businessmirror.com.ph", "apnews.com"},
        )

    def test_related_lookup_ranks_philippine_publishers_first_without_hiding_others(self):
        claim = "Manila police arrested a suspect after Batasan Hills shooting"
        local = {
            "title": claim,
            "snippet": claim,
            "link": "https://www.rappler.com/philippines/manila/batasan-shooting/",
        }
        international = {
            "title": claim,
            "snippet": claim,
            "link": "https://apnews.com/article/example",
        }
        with patch.object(retrieval.config, "SERPER_ENABLED", True), patch.object(
            retrieval.config, "SERPER_API_KEY", "fixture"
        ), patch.object(
            retrieval, "_serper_search", return_value={"organic": [international, local]}
        ):
            result = retrieval.retrieve_related_sources(claim)

        self.assertEqual(
            [source["url"] for source in result["related_sources"]],
            [local["link"], international["link"]],
        )

    def test_international_publishers_are_used_when_no_philippine_match_exists(self):
        claim = "WHO releases new public health advisory"
        international = {
            "title": claim,
            "snippet": claim,
            "link": "https://apnews.com/article/example",
        }
        with patch.object(retrieval.config, "SERPER_ENABLED", True), patch.object(
            retrieval.config, "SERPER_API_KEY", "fixture"
        ), patch.object(
            retrieval, "_serper_search", return_value={"organic": [international]}
        ):
            result = retrieval.retrieve_related_sources(claim)

        self.assertEqual(
            [source["url"] for source in result["related_sources"]],
            [international["link"]],
        )

    def test_strongest_same_publisher_result_wins_regardless_of_provider_order(self):
        claim = "Batasan Hills Quezon police arrested suspect after shooting"
        weak = {'title': 'Quezon police issue suspect advisory', 'link': 'https://www.pia.gov.ph/advisory', 'snippet': 'General public information.'}
        strong = {'title': 'Batasan Hills shooting suspect arrested by Quezon police', 'link': 'https://pia.gov.ph/shooting', 'snippet': 'Police arrested the suspect after shooting in Batasan Hills.'}
        for items in ([weak, strong], [strong, weak]):
            rows = retrieval._relevant_sources({'organic': items}, retrieval._informative_terms(claim), claim, None)
            self.assertEqual([row[1]['url'] for row in rows], [strong['link']])

    def test_same_topic_with_a_different_peso_amount_is_rejected(self):
        claim = "Customs seized 1.4 billion pesos worth of illicit vape products in Navotas."
        candidate = {"title": "Customs intercepts P1B worth of illegal vape products in Navotas",
                     "snippet": "The shipment contained illicit vape devices.", "link": "https://inquirer.net/story"}
        self.assertFalse(retrieval._is_relevant(candidate, retrieval._informative_terms(claim), claim)[0])
        candidate["title"] = "Customs intercepts ₱1.4B worth of illicit vape products in Navotas"
        self.assertTrue(retrieval._is_relevant(candidate, retrieval._informative_terms(claim), claim)[0])

    def test_peso_amounts_preserve_decimal_and_thousand_scales(self):
        self.assertEqual(retrieval._peso_amounts("P1.4B"), retrieval._peso_amounts("1,400 million pesos"))
        self.assertEqual(retrieval._peso_amounts("₱500,000"), retrieval._peso_amounts("500 thousand pesos"))
        self.assertEqual(retrieval._peso_amounts("P500 boxes"), retrieval._peso_amounts("500 pesos"))
        self.assertNotEqual(retrieval._peso_amounts("PHP 137 million"), retrieval._peso_amounts("1.4 billion pesos"))

    def test_search_query_preserves_authored_text_without_unsupported_site_operators(self):
        query = retrieval._search_query(
            "A witness wrote See less in the caption. https://facebook.com/example"
        )
        self.assertIn("See less", query)
        self.assertNotIn("https://facebook.com/example", query)
        self.assertNotIn("site:", query)
        self.assertTrue(retrieval._is_blocked_domain("facebook.com", None))

    def test_social_results_remain_blocked_after_removing_search_operators(self):
        claim = "Quezon police arrested a suspect after Batasan Hills shooting"
        social_result = {
            "title": claim,
            "snippet": claim,
            "link": "https://facebook.com/story",
        }
        with patch.object(retrieval.config, "SERPER_ENABLED", True), patch.object(
            retrieval.config, "SERPER_API_KEY", "fixture-not-live"
        ), patch.object(
            retrieval, "_serper_search", return_value={"organic": [social_result]},
        ):
            result = retrieval.retrieve_related_sources(claim)
        self.assertEqual(result["retrieval_status"], "no_results")
        self.assertEqual(result["related_sources"], [])

    def test_missing_key_is_non_fatal(self):
        # Exercise the missing-key path independently of the developer's .env.
        with patch.object(retrieval.config, "SERPER_ENABLED", True), patch.object(retrieval.config, "SERPER_API_KEY", ""):
            result = retrieval.retrieve_related_sources("sample")
        self.assertEqual(result["retrieval_status"], "unavailable_not_configured")
        self.assertEqual(result["related_sources"], [])

    def test_serper_http_failure_is_logged_without_provider_details(self):
        failure = retrieval.error.HTTPError(
            "https://google.serper.dev/search", 401, "Unauthorized", {}, None
        )
        with patch.object(retrieval, "open_provider", side_effect=failure):
            with self.assertLogs("retrieval", level="WARNING") as logged:
                self.assertIsNone(retrieval._serper_search("fixture query"))
        self.assertIn("HTTP 401", logged.output[0])
        self.assertNotIn("Unauthorized", logged.output[0])

    def test_serper_retries_once_after_a_transient_timeout(self):
        payload = io.BytesIO(b'{"organic":[]}')
        timeout = retrieval.error.URLError(TimeoutError("provider timeout"))
        with patch.object(retrieval, "open_provider", side_effect=[timeout, payload]) as provider:
            result = retrieval._serper_search("fixture query")
        self.assertEqual(result, {"organic": []})
        self.assertEqual(provider.call_count, 2)

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

    def test_titled_two_word_person_does_not_match_a_different_person(self):
        claim = 'Mayor Ana Santos opened the emergency shelter after the flood.'
        candidate = {'title': 'Mayor Maria Santos opened emergency shelter after flood',
                     'snippet': 'The mayor visited the shelter.', 'link': 'https://pna.gov.ph/articles/shelter'}
        self.assertFalse(retrieval._is_relevant(candidate, retrieval._informative_terms(claim), claim)[0])
        candidate['title'] = 'Mayor Ana Santos opened emergency shelter after flood'
        self.assertTrue(retrieval._is_relevant(candidate, retrieval._informative_terms(claim), claim)[0])

    def test_explicit_event_date_mismatch_is_not_same_event_coverage(self):
        claim = 'Customs seized illicit vape products in Navotas on October 1, 2026.'
        candidate = {'title': 'Customs seized illicit vape products in Navotas on October 1, 2025',
                     'link': 'https://pna.gov.ph/articles/seizure'}
        self.assertFalse(retrieval._is_relevant(candidate, retrieval._informative_terms(claim), claim)[0])
        candidate['title'] = 'Customs seized illicit vape products in Navotas on 1 Oktubre 2026'
        self.assertTrue(retrieval._is_relevant(candidate, retrieval._informative_terms(claim), claim)[0])
        self.assertEqual(retrieval._explicit_event_dates('2026-10-01'), retrieval._explicit_event_dates('October 1, 2026'))
        self.assertEqual(retrieval._explicit_event_dates('October 32, 2026'), set())


class FactCheckTests(unittest.TestCase):
    def test_search_does_not_display_an_unrelated_fact_check_rating(self):
        query = 'Customs seized P1.4 billion worth of illicit vape products in Navotas.'
        payload = {'claims': [{'text': 'Customs seized P137 million worth of illicit vape products in Navotas.',
            'claimReview': [{'url': 'https://verafiles.org/articles/different-seizure',
                             'title': 'Customs seizure of vape products', 'textualRating': 'False'}]}]}
        with patch.object(fact_check.config, 'GOOGLE_FACT_CHECK_ENABLED', True), patch.object(
            fact_check.config, 'GOOGLE_FACT_CHECK_API_KEY', 'test-key'
        ), patch.object(fact_check, 'open_provider', return_value=io.BytesIO(json.dumps(payload).encode())):
            result = fact_check.search_fact_checks(query)
        self.assertEqual(result['status'], 'no_results')
        self.assertEqual(result['matches'], [])

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
