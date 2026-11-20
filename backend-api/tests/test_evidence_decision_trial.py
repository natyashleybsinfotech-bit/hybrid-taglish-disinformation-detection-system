"""Regression cases for complete-claim decisions; fixtures are synthetic."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from evidence_decision import apply_evidence

MODEL = {'internal_label': 'Misleading', 'public_label': 'Potentially Misleading'}
CLAIM = 'The city opened three public schools in Manila on Monday.'


def sources(body):
    return [
        {'url': 'https://www.philstar.com/report', 'content_status': 'readable',
         'article_text': body + ' Families attended the opening of the buildings.'},
        {'url': 'https://tribune.net.ph/report', 'content_status': 'readable',
         'article_text': body + ' The local education office announced the opening.'},
    ]


class CompleteClaimEvidenceTests(unittest.TestCase):
    def test_personal_expectation_requires_full_people_and_context(self):
        claim = 'Mara and her husband Paolo Reyes are expecting their first child.'
        article = 'Singer Mara and her husband, Paolo Reyes, recently announced that they are expecting their first child.'
        result = apply_evidence(MODEL, sources(article), [], claim)
        self.assertEqual(result['public_label'], 'No Misleading Information Detected')
        for different in (
            article.replace('Paolo Reyes', 'Marco Reyes'),
            article.replace('first child', 'second child'),
            article.replace('are expecting', 'are not expecting'),
        ):
            with self.subTest(article=different):
                self.assertEqual(apply_evidence(MODEL, sources(different), [], claim)['decision_source'], 'screening_model')

    def test_preparing_to_welcome_first_child_is_not_a_completed_birth(self):
        claim = 'Mara and her husband Paolo Reyes are expecting their first child.'
        body = 'Mara and her husband, Paolo Reyes, are preparing to welcome their first child.'
        self.assertEqual(apply_evidence(MODEL, sources(body), [], claim)['public_label'], 'No Misleading Information Detected')
        for change in ('welcomed their first child', 'are not preparing to welcome their first child',
                       'are preparing to welcome their second child'):
            different = 'Mara and her husband, Paolo Reyes, ' + change + '.'
            with self.subTest(article=different):
                self.assertEqual(apply_evidence(MODEL, sources(different), [], claim)['decision_source'], 'screening_model')

    def test_advocacy_article_is_support_for_call_not_enacted_pay_raise(self):
        claim = 'ACT Teachers party-list calls for bigger education budget and higher teacher pay.'
        body = ('The ACT Teachers Party-list staged a protest in Manila, calling for a higher '
                'education budget and higher entry-level salaries for teachers.')
        result = apply_evidence(MODEL, sources(body), [], claim)
        self.assertEqual(result['public_label'], 'No Misleading Information Detected')
        self.assertEqual(len(result['evidence_urls']), 2)
        enacted = apply_evidence(MODEL, sources(body), [],
                                 'The government approved a higher education budget and higher teacher salaries.')
        self.assertEqual(enacted['decision_source'], 'screening_model')
        denied = apply_evidence(MODEL, sources('The ACT Teachers Party-list is not calling for a '
                                               'higher education budget or higher teacher salaries.'), [], claim)
        self.assertEqual(denied['decision_source'], 'screening_model')

    def test_headline_present_and_reported_past_actions_match_across_topics(self):
        cases = (
            ('The city opens three public schools in Manila.', 'The city opened three public schools in Manila.'),
            ('The council approves a new education plan.', 'The council approved a new education plan.'),
            ('The agency files charges against two officers.', 'The agency filed charges against two officers.'),
            ('The health office recommends vaccines for adults.', 'The health office recommended vaccines for adults.'),
        )
        for claim, article in cases:
            with self.subTest(claim=claim):
                result = apply_evidence(MODEL, sources(article), [], claim)
                self.assertEqual(result['public_label'], 'No Misleading Information Detected')
                self.assertEqual(len(result['evidence_urls']), 2)

    def test_action_inflection_does_not_accept_future_or_wrong_quantity(self):
        claim = 'The city opens three public schools in Manila.'
        for article in (
            'The city will open three public schools in Manila.',
            'The city opened four public schools in Manila.',
            'The city did not open three public schools in Manila.',
        ):
            with self.subTest(article=article):
                result = apply_evidence(MODEL, sources(article), [], claim)
                self.assertEqual(result['decision_source'], 'screening_model')

    def test_person_suffix_does_not_split_one_material_claim(self):
        claim = 'President Ferdinand Marcos Jr. created the National AI Council.'
        result = apply_evidence(MODEL, sources(claim), [], claim)
        self.assertEqual(result['public_label'], 'No Misleading Information Detected')
        self.assertEqual(len(result['evidence_urls']), 2)

    def test_person_suffix_still_requires_correct_actor(self):
        claim = 'President Ferdinand Marcos Jr. created the National AI Council.'
        result = apply_evidence(MODEL, sources('President Juan Santos Jr. created the National AI Council.'), [], claim)
        self.assertEqual(result['decision_source'], 'screening_model')

    def test_shortest_body_passage_excludes_unrelated_photo_caption(self):
        claim = 'President Ferdinand Marcos Jr. created the National AI Council and adopted an AI governance framework.'
        body = ('TURNOVER. President Ferdinand Marcos Jr. leads a laptop distribution at a school on November 9, 2026.\n'
                'President Ferdinand Marcos Jr. signed an executive order creating the National AI Council and adopting an AI governance framework.')
        result = apply_evidence(MODEL, sources(body), [], claim)
        self.assertEqual(result['public_label'], 'No Misleading Information Detected')
        self.assertTrue(all('TURNOVER' not in item['evidence_excerpt'] for item in result['evidence_assessments']))

    def test_news_creation_and_adoption_paraphrases_require_readable_body(self):
        claim = 'Marcos creates a National AI Council and adopts a governance framework for artificial intelligence.'
        articles = [
            {'url': 'https://www.sunstar.com.ph/manila/ai-council', 'content_status': 'readable',
             'article_text': ('President Ferdinand Marcos Jr. signed an order for the adoption of a national artificial intelligence '
                              'governance framework and creating the National Artificial Intelligence Council.The council '
                              'will oversee implementation. More agencies are joining the council.')},
            {'url': 'https://www.rappler.com/technology/ai-council', 'content_status': 'readable',
             'article_text': ('President Marcos created the National Artificial Intelligence Council and adopted an '
                              'artificial intelligence governance framework through an executive order. The government '
                              'will coordinate policy through the new council.')},
        ]
        result = apply_evidence(MODEL, articles, [], claim)
        self.assertEqual(result['public_label'], 'No Misleading Information Detected')
        self.assertEqual(len(result['evidence_urls']), 2)
        self.assertTrue(all(item['decision_eligible'] for item in result['evidence_assessments']))

    def test_creation_headline_does_not_hide_different_actor_or_future_plan(self):
        claim = 'Marcos creates a National AI Council and adopts a governance framework for artificial intelligence.'
        for body in (
            'President Santos created the National Artificial Intelligence Council and adopted an artificial intelligence governance framework.',
            'President Marcos will create the National Artificial Intelligence Council and adopt an artificial intelligence governance framework.',
            'President Marcos created the National Artificial Intelligence Council but did not adopt an artificial intelligence governance framework.',
        ):
            with self.subTest(body=body):
                result = apply_evidence(MODEL, sources(body), [], claim)
                self.assertEqual(result['decision_source'], 'screening_model')
                self.assertFalse(result['evidence_urls'])

    def test_support_exports_exact_matching_passage(self):
        result = apply_evidence(MODEL, sources(CLAIM), [], CLAIM)
        self.assertEqual(result['internal_label'], 'Non-Misleading')
        self.assertEqual(len(result['evidence_urls']), 2)
        self.assertTrue(all(item['evidence_excerpt'] == CLAIM for item in result['evidence_assessments']))

    def test_unmatched_second_assertion_prevents_support_override(self):
        result = apply_evidence(MODEL, sources(CLAIM), [], CLAIM + ' The city also opened a hospital in Cebu.')
        self.assertEqual(result['decision_source'], 'screening_model')
        self.assertFalse(result['evidence_adjusted'])
        self.assertIn('Not independently verified', result['decision_basis'])

    def test_explicit_correction_within_article_blocks_override(self):
        result = apply_evidence(MODEL, sources(CLAIM + ' False: ' + CLAIM), [], CLAIM)
        self.assertEqual(result['evidence_relationship'], 'conflicting')
        self.assertEqual(result['decision_source'], 'screening_model')
        self.assertFalse(result['evidence_urls'])

    def test_repeated_claim_followed_by_false_verdict_is_not_support(self):
        result = apply_evidence(MODEL, sources(CLAIM + ' This claim is false.'), [], CLAIM)
        self.assertEqual(result['evidence_relationship'], 'conflicting')
        self.assertEqual(result['decision_source'], 'screening_model')

    def test_hypothetical_paraphrases_do_not_establish_support(self):
        result = apply_evidence(MODEL, sources('If the city opened three public schools in Manila on Monday, residents would celebrate.'), [], CLAIM)
        self.assertEqual(result['decision_source'], 'screening_model')

    def test_headline_overlap_does_not_supply_a_body_proof(self):
        claim = 'Scarlet Witch is returning in Avengers: Doomsday'
        items = sources("Elizabeth Olsen's Scarlet Witch is making a comeback in the Marvel Cinematic Universe. The Wakandans are joining Avengers: Doomsday.")
        for item in items:
            item['title'] = claim
        result = apply_evidence(MODEL, items, [], claim)
        self.assertEqual(result['decision_source'], 'screening_model')
        self.assertTrue(all(not item['decision_eligible'] for item in result['evidence_assessments']))

    def test_no_sources_preserves_both_possible_original_labels(self):
        for model in [MODEL, {'internal_label': 'Non-Misleading', 'public_label': 'No Misleading Information Detected'}]:
            with self.subTest(model=model):
                result = apply_evidence(model, [], [], CLAIM)
                self.assertEqual(result['public_label'], model['public_label'])
                self.assertFalse(result['evidence_urls'])

    def test_different_written_quantity_does_not_establish_support(self):
        result = apply_evidence(MODEL, sources(CLAIM.replace('three', 'four')), [], CLAIM)
        self.assertEqual(result['decision_source'], 'screening_model')
        self.assertFalse(result['evidence_urls'])

    def test_relative_week_without_time_alignment_cannot_override(self):
        claim = 'The city will open three public schools in Manila next week.'
        result = apply_evidence(MODEL, sources(claim), [], claim)
        self.assertEqual(result['decision_source'], 'screening_model')
        self.assertTrue(all(not item['decision_eligible'] for item in result['evidence_assessments']))

    def test_official_source_outside_subject_scope_is_not_primary_authority(self):
        source = sources(CLAIM)[0]
        source['url'] = 'https://www.cdc.gov/school-report'
        result = apply_evidence(MODEL, [source], [], CLAIM)
        self.assertEqual(result['decision_source'], 'screening_model')

    def test_primary_health_source_with_changed_quantity_is_not_support(self):
        claim = 'The health office opened three vaccination clinics in Manila on Monday.'
        item = sources(claim.replace('three', 'four'))[0]
        item['url'] = 'https://doh.gov.ph/report'
        result = apply_evidence(MODEL, [item], [], claim)
        self.assertEqual(result['decision_source'], 'screening_model')

    def test_primary_support_cannot_hide_a_trusted_explicit_contradiction(self):
        claim = 'Drinking enough water helps prevent dehydration.'
        items = [{'url': 'https://www.cdc.gov/report', 'content_status': 'readable', 'article_text': claim},
                 {'url': 'https://www.philstar.com/report', 'content_status': 'readable', 'article_text': 'False: ' + claim}]
        result = apply_evidence(MODEL, items, [], claim)
        self.assertEqual(result['evidence_relationship'], 'conflicting')
        self.assertEqual(result['decision_source'], 'screening_model')

    def test_supporting_one_statement_does_not_hide_an_explicit_debunk(self):
        second = 'The city opened a hospital in Cebu.'
        result = apply_evidence({'internal_label': 'Non-Misleading', 'public_label': 'No Misleading Information Detected'},
                                sources(CLAIM + ' False: ' + second), [], CLAIM + ' ' + second)
        self.assertEqual(result['internal_label'], 'Misleading')
        self.assertEqual(result['decision_source'], 'verified_evidence')
        self.assertTrue(all(item['evidence_excerpt'] == 'False: ' + second for item in result['evidence_assessments']))


if __name__ == '__main__':
    unittest.main()
