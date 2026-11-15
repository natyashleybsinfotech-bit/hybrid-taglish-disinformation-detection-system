import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from evidence_decision import _article_relation, apply_evidence


MODEL_NO = {"internal_label": "Non-Misleading", "public_label": "No Misleading Information Detected"}
MODEL_YES = {"internal_label": "Misleading", "public_label": "Potentially Misleading"}


class EvidenceDecisionTests(unittest.TestCase):
    def test_gma_fuel_rollback_report_supports_matching_future_price_claim(self):
        claim = "Motorists should expect another round of rollback in pump prices to be implemented in the coming week."
        article = "Another major fuel rollback is expected next week. Pump prices will go down."
        relationship, _ = _article_relation(claim, article)
        self.assertEqual(relationship, "supports")

        result = apply_evidence(MODEL_YES, [{
            "url": "https://www.gmanetwork.com/news/story",
            "content_status": "readable",
            "article_text": article,
        }], [], claim)
        self.assertEqual(result["evidence_relationship"], "supports")
        self.assertEqual(result["decision_source"], "screening_model")
        self.assertEqual(result["public_label"], MODEL_YES["public_label"])

    def test_negated_fuel_rollback_does_not_support_claim(self):
        claim = "Motorists should expect another round of rollback in pump prices to be implemented in the coming week."
        article = "Motorists should not expect another round of rollback in pump prices next week."
        relationship, _ = _article_relation(claim, article)
        self.assertNotEqual(relationship, "supports")

    def test_questions_hypotheticals_and_embedded_quotes_do_not_reverse_warning(self):
        claim = 'The city opened three public schools in Manila on Monday'
        for text in (claim + '?', 'If ' + claim + ', the mayor would celebrate.',
                     'Investigators asked whether ' + claim + '.',
                     'The headline reads “' + claim + '”.'):
            with self.subTest(text=text):
                sources = [{'url': f'https://{host}.example/report', 'content_status': 'readable', 'article_text': text} for host in ('a', 'b')]
                decision = apply_evidence(MODEL_YES, sources, [], claim)
                self.assertFalse(decision['evidence_adjusted'])
                self.assertEqual(decision['supporting_source_count'], 0)

    def test_www_aliases_are_not_independent_support(self):
        claim = 'The city opened three public schools in Manila on Monday.'
        sources = [{'url': 'https://news.example/story', 'content_status': 'readable', 'article_text': claim + ' Officials attended.'},
                   {'url': 'https://www.news.example/update', 'content_status': 'readable', 'article_text': claim + ' Residents attended.'}]
        self.assertFalse(apply_evidence(MODEL_YES, sources, [], claim)['evidence_adjusted'])

    def test_question_with_a_false_marker_is_not_a_debunk(self):
        claim = 'The city opened three public schools in Manila on Monday'
        source = {'url': 'https://news.example/report', 'content_status': 'readable', 'article_text': 'False: ' + claim + '?'}
        self.assertFalse(apply_evidence(MODEL_NO, [source], [], claim)['evidence_adjusted'])

    def test_negated_or_attributed_debunk_does_not_override(self):
        claim = "The city opened three public schools in Manila on Monday"
        for body in (
            "It is not false that " + claim + ".",
            "It is not misleading to report that " + claim + ".",
            'A post says "False: ' + claim + '." Officials have not verified it.',
            '"False: ' + claim + '."',
            "Ayon sa post, peke: " + claim + ".",
        ):
            with self.subTest(body=body):
                source = {"url": "https://check.example/report", "content_status": "readable", "article_text": body}
                result = apply_evidence(MODEL_NO, [source], [], claim)
                self.assertEqual(result["public_label"], MODEL_NO["public_label"])
                self.assertFalse(result["evidence_adjusted"])
                self.assertNotEqual(result["evidence_relationship"], "contradicts")

    def test_partial_word_does_not_establish_support(self):
        claim = "The city opened three public schools in Manila on Monday"
        sources = [{"url": f"https://{host}.example/report", "content_status": "readable", "article_text": claim + "ish."} for host in ("a", "b")]
        result = apply_evidence(MODEL_YES, sources, [], claim)
        self.assertEqual(result["supporting_source_count"], 0)
        self.assertFalse(result["evidence_adjusted"])

    def test_two_independent_readable_assertions_can_reverse_model_warning(self):
        claim = "The Bureau of Customs destroyed 3174 boxes of illicit vape products worth 1.4 billion pesos in Navotas."
        sources = [
            {"url": "https://www.philstar.com/story", "content_status": "readable", "article_text": claim + " Customs officials supervised the disposal."},
            {"url": "https://tribune.net.ph/report", "content_status": "readable", "article_text": claim + " The shipment had been seized earlier."},
        ]
        result = apply_evidence(MODEL_YES, sources, [], claim)
        self.assertEqual(result["public_label"], "No Misleading Information Detected")
        self.assertTrue(result["evidence_adjusted"])
        self.assertEqual(result["evidence_relationship"], "supports")

    def test_two_urls_from_the_same_publisher_are_not_independent(self):
        claim = "The city opened three public schools in Manila on Monday."
        sources = [
            {"url": "https://www.philstar.com/story", "content_status": "readable", "article_text": claim + " Officials attended the opening."},
            {"url": "https://news.philstar.com/update", "content_status": "readable", "article_text": claim + " Residents attended the opening."},
        ]
        result = apply_evidence(MODEL_YES, sources, [], claim)
        self.assertEqual(result["public_label"], MODEL_YES["public_label"])
        self.assertEqual(result["decision_source"], "screening_model")

    def test_untrusted_publishers_do_not_count_toward_override(self):
        claim = "The city opened three public schools in Manila on Monday."
        sources = [
            {"url": "https://one.example/story", "content_status": "readable", "article_text": claim + " Officials attended."},
            {"url": "https://two.example/report", "content_status": "readable", "article_text": claim + " Residents attended."},
        ]
        result = apply_evidence(MODEL_YES, sources, [], claim)
        self.assertEqual(result["public_label"], MODEL_YES["public_label"])
        self.assertEqual(result["supporting_source_count"], 0)

    def test_near_identical_syndicated_articles_do_not_count_twice(self):
        claim = "The city opened three public schools in Manila on Monday."
        article = claim + " City officials said the schools will serve local families."
        sources = [
            {"url": "https://www.philstar.com/story", "content_status": "readable", "article_text": article},
            {"url": "https://tribune.net.ph/report", "content_status": "readable", "article_text": article},
        ]
        result = apply_evidence(MODEL_YES, sources, [], claim)
        self.assertEqual(result["public_label"], MODEL_YES["public_label"])
        self.assertEqual(result["decision_source"], "screening_model")

    def test_present_tense_boc_vape_headline_matches_independent_reports(self):
        claim = "BOC destroys P1.4 billion smuggled vape products."
        sources = [
            {
                "url": "https://www.philstar.com/business/2026/10/02/boc-vape-products",
                "content_status": "readable",
                "article_text": (
                    "MANILA, Philippines — The Bureau of Customs (BOC) destroyed yesterday "
                    "3,174 boxes of smuggled vape products from China valued at P1.4 billion."
                ),
            },
            {
                "url": "https://tribune.net.ph/2026/10/02/boc-vape-products",
                "content_status": "readable",
                "article_text": (
                    "BUREAU of Customs personnel condemn and destroy more than P1.4 billion "
                    "worth of illicit vape products on Thursday. The disposal represents the "
                    "largest single-operation seizure of smuggled vape products and devices "
                    "in the agency's history."
                ),
            },
        ]

        result = apply_evidence(MODEL_YES, sources, [], claim)

        self.assertEqual(
            [item["relationship"] for item in result["evidence_assessments"]],
            ["supports", "supports"],
        )
        self.assertEqual(result["public_label"], MODEL_NO["public_label"])
        self.assertEqual(result["decision_source"], "verified_evidence")
        self.assertEqual(result["supporting_source_count"], 2)

    def test_one_trusted_article_supporting_all_material_details_is_not_enough(self):
        claim = "The Bureau of Customs destroyed 3174 boxes of illicit vape products worth 1.4 billion pesos in Navotas."
        source = {
            "url": "https://www.philstar.com/business/2026/10/02/boc-vape-products",
            "content_status": "readable",
            "article_text": (
                "The Bureau of Customs destroyed 3,174 boxes of illicit vape products worth "
                "1.4 billion pesos in Navotas. Officials supervised the disposal."
            ),
        }

        result = apply_evidence(MODEL_YES, [source], [], claim)

        self.assertEqual(result["evidence_assessments"][0]["relationship"], "supports")
        self.assertEqual(result["public_label"], MODEL_YES["public_label"])
        self.assertEqual(result["decision_source"], "screening_model")
        self.assertEqual(result["supporting_source_count"], 1)
        self.assertFalse(result["evidence_adjusted"])

    def test_jensen_huang_liveblog_search_preview_is_not_verified_support(self):
        claim = (
            "Nvidia CEO Jensen Huang has called it quits after revelations about two "
            "extramarital affairs, including one with an alleged Chinese spy."
        )
        source = {
            "url": (
                "https://www.aljazeera.com/news/liveblog/2026/11/12/"
                "live-jensen-huang-resigns-as-nvidia-ceo-as-affairs-raise-security-concerns"
            ),
            "content_status": "inaccessible",
            "search_title": "Updates: Jensen Huang resigns as Nvidia CEO amid affairs, security concerns",
            "search_snippet": (
                "Jensen Huang has resigned after revelations emerged that he had two "
                "extramarital affairs, including one with an alleged Chinese spy."
            ),
        }

        result = apply_evidence(MODEL_YES, [source], [], claim)

        self.assertEqual(result["public_label"], MODEL_YES["public_label"])
        self.assertEqual(result["decision_source"], "screening_model")
        self.assertEqual(result["evidence_relationship"], "unverified")
        self.assertEqual(result["supporting_source_count"], 0)
        self.assertFalse(result["evidence_adjusted"])

        readable_source = {
            **source,
            "content_status": "readable",
            "title": "Updates: Jensen Huang resigns as Nvidia CEO amid affairs, security concerns",
            "article_text": claim,
        }
        verified = apply_evidence(MODEL_YES, [readable_source], [], claim)
        self.assertEqual(verified["public_label"], MODEL_YES["public_label"])
        self.assertEqual(verified["decision_source"], "screening_model")
        self.assertEqual(verified["evidence_relationship"], "supports")

    def test_jensen_huang_readable_liveblog_summary_supports_qualified_claim(self):
        claim = (
            "Nvidia CEO Jensen Huang has called it quits after revelations about two "
            "extramarital affairs, including one with an alleged Chinese spy."
        )
        body = (
            "Jensen Huang resigned as Nvidia CEO after reports of relationships with "
            "two women, one allegedly a Chinese spy.\n"
            "Series of scandals: The decision followed reports that Huang had a "
            "relationship with an Nvidia executive. He was already under scrutiny "
            "after reports of an affair with another woman who was allegedly working "
            "as a spy for China."
        )
        source = {
            "url": (
                "https://edition.cnn.com/2026/11/11/business/live-news/"
                "nvidia-jensen-huang-investigation-fallout"
            ),
            "content_status": "readable",
            "title": "Jensen Huang summoned to testify before Congress after resigning as Nvidia CEO",
            "article_text": body,
        }

        supported = apply_evidence(MODEL_YES, [source], [], claim)
        self.assertEqual(supported["public_label"], MODEL_YES["public_label"])
        self.assertEqual(supported["decision_source"], "screening_model")
        self.assertEqual(supported["evidence_relationship"], "supports")
        self.assertEqual(supported["supporting_source_count"], 1)

        unqualified_body = body.replace("allegedly ", "")
        unsupported = apply_evidence(
            MODEL_YES, [{**source, "article_text": unqualified_body}], [], claim
        )
        self.assertEqual(unsupported["public_label"], MODEL_YES["public_label"])
        self.assertFalse(unsupported["evidence_adjusted"])

    def test_primary_health_source_can_support_a_short_paraphrase(self):
        claim = "Drinking enough water helps prevent dehydration."
        source = {
            "url": "https://www.cdc.gov/healthy-weight-growth/water-healthy-drinks/",
            "content_status": "readable",
            "article_text": "Drinking water can prevent dehydration, which may cause unclear thinking.",
        }

        result = apply_evidence(MODEL_YES, [source], [], claim)

        self.assertEqual(result["public_label"], MODEL_NO["public_label"])
        self.assertEqual(result["evidence_rule"], "scoped_primary_authority")
        self.assertEqual(result["decision_source"], "verified_evidence")
        self.assertEqual(result["evidence_relationship"], "supports")

    def test_exact_publisher_headline_needs_body_corroboration(self):
        claim = "Scarlet Witch is returning in Avengers: Doomsday"
        source = {
            "url": "https://www.gmanetwork.com/news/story",
            "content_status": "readable",
            "title": "Scarlet Witch is returning in 'Avengers: Doomsday'",
            "article_text": (
                "Elizabeth Olsen's Scarlet Witch is making a comeback in the Marvel Cinematic Universe. "
                "The Wakandans, led by Shuri, are also joining Avengers: Doomsday."
            ),
        }

        supported = apply_evidence(MODEL_YES, [source], [], claim)
        self.assertEqual(supported["public_label"], MODEL_YES["public_label"])
        self.assertEqual(supported["evidence_assessments"][0]["relationship"], "supports")

        source["article_text"] = "An unrelated story about Marvel movies and television."
        unsupported = apply_evidence(MODEL_YES, [source], [], claim)
        self.assertEqual(unsupported["public_label"], MODEL_YES["public_label"])
        self.assertEqual(unsupported["evidence_assessments"][0]["relationship"], "related")

        source["article_text"] = (
            "Elizabeth Olsen's Scarlet Witch is not making a comeback in the Marvel Cinematic Universe. "
            "Avengers: Doomsday is a separate film."
        )
        contradicted = apply_evidence(MODEL_YES, [source], [], claim)
        self.assertEqual(contradicted["public_label"], MODEL_YES["public_label"])
        self.assertEqual(contradicted["evidence_assessments"][0]["relationship"], "related")

    def test_lto_license_suspension_headline_matches_readable_publisher_report(self):
        claim = "LTO suspends BINI Mikha’s driver’s license for 90 days"
        source = {
            "url": "https://www.philstar.com/nation/2026/11/11/lto-suspends-bini-mikhas-license",
            "content_status": "readable",
            "title": "LTO suspends BINI Mikha’s driver’s license for 90 days",
            "article_text": (
                "The Land Transportation Office has suspended the driver’s license of a member of P-pop group BINI. "
                "A viral video showed BINI member Mikha texting while driving, following which the agency issued "
                "a show-cause order against her. The preventive suspension of Mikha’s license will last 90 days."
            ),
        }

        result = apply_evidence(MODEL_YES, [source], [], claim)

        self.assertEqual(result["evidence_assessments"][0]["relationship"], "supports")
        self.assertEqual(result["public_label"], MODEL_YES["public_label"])
        self.assertEqual(result["decision_source"], "screening_model")

    def test_related_allegation_does_not_hide_reported_license_suspension(self):
        claim = "LTO suspends BINI Mikha’s driver’s license for 90 days"
        source = {
            "url": "https://www.gmanetwork.com/news/story",
            "content_status": "readable",
            "title": "BINI's Mikha Lim surrenders driver's license to LTO",
            "article_text": (
                "BINI member Mikha Lim has surrendered her driver's license to the Land Transportation Office (LTO) "
                "after she was issued a Show Cause Order over alleged cellphone use while driving. "
                "According to a report, the P-pop star personally went to the LTO Central Office, accompanied by her manager, "
                "to surrender her license, which was placed under a 90-day preventive suspension pending investigation."
            ),
        }

        result = apply_evidence(MODEL_YES, [source], [], claim)

        self.assertEqual(result["evidence_assessments"][0]["relationship"], "supports")
        self.assertEqual(result["public_label"], MODEL_YES["public_label"])

    def test_one_trusted_source_cannot_override_a_model_warning(self):
        claim = "Drinking enough water helps prevent dehydration."
        source = {
            "url": "https://www.philstar.com/health/article",
            "content_status": "readable",
            "article_text": "Drinking water can prevent dehydration.",
        }

        result = apply_evidence(MODEL_YES, [source], [], claim)

        self.assertEqual(result["public_label"], MODEL_YES["public_label"])
        self.assertEqual(result["decision_source"], "screening_model")
        self.assertEqual(result["evidence_relationship"], "supports")

    def test_single_secondary_source_cannot_override_a_model_warning(self):
        claim = "Drinking enough water helps prevent dehydration."
        source = {
            "url": "https://news.example/health",
            "content_status": "readable",
            "article_text": "Drinking water can prevent dehydration, which may cause unclear thinking.",
        }

        result = apply_evidence(MODEL_YES, [source], [], claim)

        self.assertEqual(result["public_label"], MODEL_YES["public_label"])
        self.assertEqual(result["decision_source"], "screening_model")
        self.assertFalse(result["evidence_adjusted"])

    def test_one_trusted_article_supporting_noisy_caption_is_not_enough(self):
        claim = "pholo PIA MRT-3, planong isapribado sa 2027 October 22, 2026 NEWS"
        source = {
            "url": "https://www.philstar.com/pilipino-star-ngayon/metro/2026/10/24/2565360/mrt-3-target-maisapribado-sa-2027",
            "content_status": "readable",
            "article_text": "MANILA, Philippines — Target ng Department of Transportation (DOTr) na maisapribado ang operasyon ng Metro Rail Transit Line 3 (MRT-3) sa kalagitnaan ng 2027.",
        }

        result = apply_evidence(MODEL_YES, [source], [], claim)

        self.assertEqual(result["evidence_assessments"][0]["relationship"], "supports")
        self.assertEqual(result["evidence_relationship"], "supports")
        self.assertEqual(result["supporting_source_count"], 1)
        self.assertEqual(result["public_label"], MODEL_YES["public_label"])
        self.assertEqual(result["decision_source"], "screening_model")
        self.assertFalse(result["evidence_adjusted"])

    def test_explicit_readable_debunk_can_reverse_model_clear(self):
        claim = "The Bureau of Customs destroyed 3174 boxes of illicit vape products worth 1.4 billion pesos in Cebu."
        sources = [
            {"url": "https://www.snopes.com/story", "content_status": "readable",
             "article_text": "False: " + claim + " The event happened in Navotas, not Cebu."},
            {"url": "https://www.politifact.com/story", "content_status": "readable",
             "article_text": "False: " + claim + " Customs officials place the disposal in Navotas, not Cebu."},
        ]
        result = apply_evidence(MODEL_NO, sources, [], claim)
        self.assertEqual(result["public_label"], "Potentially Misleading")
        self.assertTrue(result["evidence_adjusted"])

    def test_conflict_blocks_override(self):
        claim = "The Bureau of Customs destroyed 3174 boxes of illicit vape products worth 1.4 billion pesos in Navotas."
        sources = [
            {"url": "https://www.philstar.com/story", "content_status": "readable", "article_text": claim + " Officials confirmed the event."},
            {"url": "https://tribune.net.ph/story", "content_status": "readable", "article_text": "False: " + claim + " The agency denied the report."},
        ]
        result = apply_evidence(MODEL_YES, sources, [], claim)
        self.assertEqual(result["public_label"], "Potentially Misleading")
        self.assertEqual(result["evidence_relationship"], "conflicting")
        self.assertFalse(result["evidence_adjusted"])

    def test_one_trusted_contradiction_does_not_override_model_clear(self):
        claim = "The city opened three public schools in Manila on Monday."
        source = {
            "url": "https://www.philstar.com/story",
            "content_status": "readable",
            "article_text": "False: " + claim + " The city opened them on Tuesday instead.",
        }
        result = apply_evidence(MODEL_NO, [source], [], claim)
        self.assertEqual(result["public_label"], MODEL_NO["public_label"])
        self.assertEqual(result["decision_source"], "screening_model")
        self.assertFalse(result["evidence_adjusted"])

    def test_changed_date_amount_or_qualification_is_not_support(self):
        claim = "Umano, 3174 boxes worth 1.4 billion pesos were destroyed in Navotas on October 1 2026."
        different = "3174 boxes worth 1.4 billion pesos were seized in Navotas on March 21 2026."
        sources = [{"url": f"https://{host}.example/story", "content_status": "readable", "article_text": different}
                   for host in ("a", "b")]
        result = apply_evidence(MODEL_YES, sources, [], claim)
        self.assertEqual(result["public_label"], "Potentially Misleading")
        self.assertEqual(result["evidence_relationship"], "related")

    def test_article_quoting_a_viral_post_is_not_direct_support(self):
        claim = "The Bureau of Customs destroyed 3174 boxes of illicit vape products worth 1.4 billion pesos in Navotas."
        sources = [{"url": f"https://{host}.example/report", "content_status": "readable",
                    "article_text": "A viral post claims that " + claim + f" Reporter {host} is investigating."}
                   for host in ("a", "b")]
        result = apply_evidence(MODEL_YES, sources, [], claim)
        self.assertEqual(result["public_label"], "Potentially Misleading")
        self.assertFalse(result["evidence_adjusted"])

    def test_related_reading_never_changes_the_model_label(self):
        # Each case has lexical overlap but lacks verified claim-level entailment.
        cases = {
            "official_other_event": [{"title": "Agency confirms a different event", "url": "https://doh.gov.ph/report"}],
            "same_names_different_event": [{"title": "Mayor Santos visits another city", "url": "https://one.example/report"}],
            "wrong_date_location": [{"title": "Flood on June 5 in Cebu", "url": "https://one.example/report"}],
            "contradictory_quantities": [{"title": "12 injured", "url": "https://one.example/report"}],
            "negation": [{"title": "Agency did not approve the plan", "url": "https://one.example/report"}],
            "repeated_original": [{"title": "Wire report repeated", "url": "https://one.example/report"}, {"title": "Wire report repeated", "url": "https://two.example/report"}],
            "conflict": [{"title": "Agency approves plan", "url": "https://one.example/report"}, {"title": "Agency denies plan", "url": "https://two.example/report"}],
        }
        for name, sources in cases.items():
            with self.subTest(name=name):
                result = apply_evidence(MODEL_YES, sources, [])
                self.assertEqual(result["public_label"], MODEL_YES["public_label"])
                self.assertEqual(result["decision_source"], "screening_model")
                self.assertEqual(result["evidence_relationship"], "unverified")
                self.assertEqual(result["supporting_source_count"], 0)

    def test_similar_and_conflicting_fact_checks_do_not_override(self):
        for rating in ("True", "False"):
            match = {"claim": "Similar but different claim", "url": "https://check.example", "rating": rating, "match_strength": .99, "matched_term_count": 8}
            result = apply_evidence(MODEL_NO, [], [match])
            self.assertEqual(result["public_label"], MODEL_NO["public_label"])
            self.assertEqual(result["strong_fact_check_matches"], [])
            self.assertEqual(result["evidence_relationship"], "unverified")

    def test_no_results_or_timeout_leave_the_prediction_untouched(self):
        result = apply_evidence(MODEL_NO, [], [])
        self.assertEqual(result["public_label"], MODEL_NO["public_label"])
        self.assertEqual(result["evidence_relationship"], "not_assessed")


if __name__ == "__main__":
    unittest.main()
