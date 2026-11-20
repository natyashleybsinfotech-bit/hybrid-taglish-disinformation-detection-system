import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import gemini_evidence as reader
import gemini_classifier_trial as primary
import evidence_decision as decision

CLAIM = 'The city opened three public schools in Manila on Monday.'
ARTICLE = CLAIM + ' Families attended the opening ceremony.'
SOURCES = [{'url': 'https://www.philstar.com/report', 'content_status': 'readable', 'article_text': ARTICLE}]


def response_payload(claim=CLAIM, quote=CLAIM, source_id='s1'):
    return {'claim': claim, 'assessments': [{'source_id': source_id, 'relationship': 'supports',
        'passage_ids': ['s1p1' if quote == CLAIM else 'invented-passage'], 'reason_en': 'The article states the same event and details.',
        'reason_tl': 'Pareho ang pangyayari at detalye sa artikulo.'}]}


class Response:
    def __init__(self, value):
        self.payload = json.dumps(value).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, size): return self.payload[:size]


def provider_response(value=None, finish='STOP'):
    return Response({'candidates': [{'finishReason': finish, 'content': {'parts': [{'text': json.dumps(value or response_payload())}]}}]})


class GeminiEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config = patch.multiple(reader.config, GEMINI_ENABLED=True, GEMINI_API_KEY='test-key-not-secret',
            GEMINI_MODEL='gemini-3.5-flash-lite', GEMINI_TIMEOUT_SECONDS=10,
            GEMINI_REQUESTS_PER_MINUTE=4, GEMINI_REQUESTS_PER_DAY=5,
            GEMINI_BUDGET_PATH=Path(self.temp.name)/'budget.json')
        self.config.start();reader._cache.clear();reader._minute.clear()
    def tearDown(self):
        self.config.stop();self.temp.cleanup()

    def test_valid_source_quote_is_accepted_and_cached(self):
        with patch.object(reader, 'open_provider', return_value=provider_response()) as call:
            result=reader.assess_claim(CLAIM,SOURCES)
            self.assertEqual(result['status'],'assessed')
            self.assertEqual(result['assessments'][0]['url'],SOURCES[0]['url'])
            self.assertEqual(result['assessments'][0]['evidence_excerpt'],ARTICLE)
            self.assertTrue(reader.assess_claim(CLAIM,SOURCES)['cache_hit'])
            call.assert_called_once()
            self.assertNotIn('test-key-not-secret',call.call_args.args[0].full_url)
        budget=json.loads((Path(self.temp.name)/'budget.json').read_text())
        self.assertEqual(set(budget),{'date','count'})

    def test_invented_quote_unknown_source_or_changed_claim_is_rejected(self):
        for value in [response_payload(quote='The city opened a hospital in Cebu.'),
                      response_payload(source_id='invented'),response_payload(claim='A different claim')]:
            with self.subTest(value=value),patch.object(reader,'open_provider',return_value=provider_response(value)):
                self.assertEqual(reader.assess_claim(CLAIM,SOURCES)['status'],'invalid_response')

    def test_missing_quote_and_invented_explanation_link_are_rejected(self):
        for field,value in [('passage_ids',[]),('reason_en','See https://invented.example/report')]:
            payload=response_payload();payload['assessments'][0][field]=value
            with self.subTest(field=field),patch.object(reader,'open_provider',return_value=provider_response(payload)):
                self.assertEqual(reader.assess_claim(CLAIM,SOURCES)['status'],'invalid_response')

    def test_unreadable_or_oversized_source_does_not_call_provider(self):
        for sources in [[{**SOURCES[0],'content_status':'inaccessible'}],
                        [{**SOURCES[0],'article_text':'x'*24001}]]:
            with patch.object(reader,'open_provider') as call:
                self.assertNotEqual(reader.assess_claim(CLAIM,sources)['status'],'assessed');call.assert_not_called()

    def test_reporter_credit_is_not_required_as_an_event_actor(self):
        quote=CLAIM
        sources=[{**SOURCES[0],'url':'https://www.cdc.gov/report'}]
        # CDC is scoped only for health, so inspect eligibility independently.
        item={'url':sources[0]['url'],'relationship':'supports','reason':'Same event',
              'reason_tl':'Parehong pangyayari','evidence_excerpt':quote,'decision_eligible':True}
        with patch.object(decision,'assess_claim',return_value={'status':'assessed','assessments':[item]}):
            result=decision.apply_evidence({'public_label':'Potentially Misleading','internal_label':'Misleading'},sources,[],CLAIM+' | via Jonas Sulit, Abante')
        self.assertTrue(result['evidence_assessments'][0]['decision_eligible'])
        self.assertNotEqual(result['decision_source'],'verified_evidence')

    def test_event_person_cannot_be_removed_as_reporter_credit(self):
        claim='Mayor Jonas Sulit opened three public schools in Manila on Monday.'
        item={'url':SOURCES[0]['url'],'relationship':'supports','reason':'Same event',
              'reason_tl':'Parehong pangyayari','evidence_excerpt':CLAIM,'decision_eligible':True}
        with patch.object(decision,'assess_claim',return_value={'status':'assessed','assessments':[item]}):
            result=decision.apply_evidence({'public_label':'Potentially Misleading','internal_label':'Misleading'},SOURCES,[],claim)
        self.assertFalse(result['evidence_assessments'][0]['decision_eligible'])

    def test_original_photo_report_requires_provenance_date_and_no_conflict(self):
        claim='MMDA personnel monitored orange barriers on Roxas Boulevard on November 14, 2026.'
        url='https://www.manilatimes.net/2026/11/14/photos/example/123/amp'
        source={'url':url,'content_status':'readable','article_text':claim,
                'content_kind':'publisher_photo_report','provenance_verified':True,
                'photo_credit':'Example Reporter','date_published':'2026-11-14T20:00:00+08:00'}
        assessment={'url':url,'relationship':'supports','reason':'Caption describes the same dated event.',
                    'reason_tl':'Parehong pangyayari at petsa.','evidence_excerpt':claim,'decision_eligible':True}
        model={'public_label':'Potentially Misleading','internal_label':'Misleading'}
        with patch.object(decision,'assess_claim',return_value={'status':'assessed','assessments':[assessment]}):
            result=decision.apply_evidence(model,[source],[],claim)
            self.assertEqual(result['evidence_rule'],'direct_publisher_photo_report')
            self.assertEqual(result['public_label'],'No Misleading Information Detected')
            for field in ['provenance_verified','photo_credit','date_published','content_kind']:
                incomplete=dict(source);incomplete.pop(field)
                self.assertEqual(decision.apply_evidence(model,[incomplete],[],claim)['decision_source'],'screening_model')
            self.assertEqual(decision.apply_evidence(model,[source],[],claim.replace('14,','15,'))['decision_source'],'screening_model')
        opposing_url='https://www.philstar.com/opposing-report'
        opposing={**assessment,'url':opposing_url,'relationship':'contradicts','evidence_excerpt':'MMDA personnel did not monitor orange barriers on Roxas Boulevard on November 14, 2026.'}
        opposing_source={'url':opposing_url,'content_status':'readable','article_text':opposing['evidence_excerpt']}
        with patch.object(decision,'assess_claim',return_value={'status':'assessed','assessments':[assessment,opposing]}):
            result=decision.apply_evidence(model,[source,opposing_source],[],claim)
        self.assertEqual(result['decision_source'],'screening_model')
        self.assertEqual(result['evidence_relationship'],'conflicting')

    def test_taglish_place_alias_preserves_support_but_different_city_does_not(self):
        quote='The city opened three schools in Manila.'
        source={**SOURCES[0],'article_text':quote}
        item={'url':source['url'],'relationship':'supports','reason':'Same event','reason_tl':'Parehong pangyayari',
              'evidence_excerpt':quote,'decision_eligible':True}
        with patch.object(decision,'assess_claim',return_value={'status':'assessed','assessments':[item]}):
            result=decision.apply_evidence({'public_label':'Potentially Misleading','internal_label':'Misleading'},[source],[],
                                         'Nagbukas ng tatlong paaralan sa Maynila ang lungsod.')
            self.assertTrue(result['evidence_assessments'][0]['decision_eligible'])
            wrong=decision.apply_evidence({'public_label':'Potentially Misleading','internal_label':'Misleading'},[source],[],
                                         'Nagbukas ng tatlong paaralan sa Cebu ang lungsod.')
        rejected=wrong['evidence_assessments'][0]
        self.assertFalse(rejected['decision_eligible'])
        self.assertEqual(rejected['validation_issues'],['location'])
        self.assertIn('locations',rejected['reason'])
        self.assertIn('mga lugar',rejected['reason_tl'])
        self.assertNotIn('Parehong pangyayari',rejected['reason_tl'])

    def test_invalid_quote_exposes_only_fixed_validation_category(self):
        with patch.object(reader,'open_provider',return_value=provider_response(response_payload(quote='An invented detail not in the body.'))):
            result=reader.assess_claim(CLAIM,SOURCES)
        self.assertEqual(result['status'],'invalid_response')
        self.assertEqual(result['validation_error'],'passage_reference')
        self.assertNotIn('invented detail',str(result))

    def test_cdc_antibiotic_guidance_is_within_its_public_health_scope(self):
        self.assertIsNotNone(decision._primary_authority_for_claim('https://www.cdc.gov/antibiotic-use/guide','Antibiotics treat infections caused by viruses.'))
        self.assertIsNone(decision._primary_authority_for_claim('https://www.cdc.gov/news','A singer released a music video.'))

    def test_passages_preserve_original_text_and_reject_cross_source_ids(self):
        original='First sentence.\nSecond paragraph with a factual date: November 14, 2026.'
        passages=reader._source_passages('s1',original)
        self.assertEqual(' '.join(p['text'] for p in passages),' '.join(original.split()))
        source={'source_id':'s1','url':SOURCES[0]['url'],'article_text':original,'passages':passages}
        payload=response_payload();payload['assessments'][0]['passage_ids']=['s2p1']
        with self.assertRaises(ValueError):reader._validate_passage_payload(payload,CLAIM,[source])
        payload['assessments'][0]['passage_ids']=['s1p1'];payload['assessments'][0]['quotes']=['A fabricated quotation.']
        with self.assertRaises(ValueError):reader._validate_passage_payload(payload,CLAIM,[source])

    def test_local_semantic_trial_can_use_one_validated_source_but_never_related(self):
        model={'internal_label':'Misleading','public_label':'Potentially Misleading'}
        support={'url':SOURCES[0]['url'],'relationship':'supports','reason':'Same complete event',
                 'reason_tl':'Parehong buong pangyayari','evidence_excerpt':CLAIM,'decision_eligible':True}
        with patch.object(decision.config,'EVIDENCE_POLICY','semantic_single_source_trial'):
            with patch.object(decision,'assess_claim',return_value={'status':'assessed','assessments':[support]}):
                result=decision.apply_evidence(model,SOURCES,[],CLAIM)
                self.assertEqual(result['public_label'],'No Misleading Information Detected')
                self.assertEqual(result['evidence_rule'],'validated_single_source_trial')
                changed=decision.apply_evidence(model,SOURCES,[],CLAIM.replace('three','four'))
                self.assertEqual(changed['decision_source'],'screening_model')
            for status,relationship,eligible in [('assessed','related',False),('unavailable','supports',True),('assessed','conflicting',False)]:
                with patch.object(decision,'assess_claim',return_value={'status':status,'assessments':[{**support,'relationship':relationship,'decision_eligible':eligible}]}):
                    result=decision.apply_evidence(model,SOURCES,[],CLAIM)
                self.assertEqual(result['decision_source'],'screening_model')

    def test_local_semantic_trial_does_not_override_conflicting_evidence(self):
        first={'url':SOURCES[0]['url'],'relationship':'supports','reason':'Supports','reason_tl':'Sumusuporta',
               'evidence_excerpt':CLAIM,'decision_eligible':True}
        other={'url':'https://tribune.net.ph/report','content_status':'readable','article_text':CLAIM}
        opposing={**first,'url':other['url'],'relationship':'contradicts'}
        with patch.object(decision.config,'EVIDENCE_POLICY','semantic_single_source_trial'),patch.object(decision,'assess_claim',return_value={'status':'assessed','assessments':[first,opposing]}):
            result=decision.apply_evidence({'internal_label':'Misleading','public_label':'Potentially Misleading'},SOURCES+[other],[],CLAIM)
        self.assertEqual(result['decision_source'],'screening_model')
        self.assertEqual(result['evidence_relationship'],'conflicting')

    def test_semantic_trial_is_blocked_by_production_configuration_validation(self):
        with patch.object(reader.config,'APP_ENV','production'),patch.object(reader.config,'EVIDENCE_POLICY','semantic_single_source_trial'):
            with self.assertRaisesRegex(RuntimeError,'local-only'):
                reader.config.validate_runtime_config()

    def test_primary_classifier_with_no_sources_returns_unscored_label_and_native_search(self):
        value={'claim':CLAIM,'assessments':[],'label':'Non-Misleading','self_reported_score':74,
               'primary_reason_en':'No sufficient evidence; this is an unverified classification.',
               'primary_reason_tl':'Walang sapat na ebidensiya; hindi pa beripikado.'}
        with patch.object(reader,'open_provider',return_value=provider_response(value)) as call:
            result=primary.classify_claim(CLAIM,[],grounding=True)
        self.assertEqual(result['status'],'classified')
        self.assertEqual(result['label'],'Non-Misleading')
        self.assertEqual(result['self_reported_score'],74)
        request=call.call_args.args[0]
        self.assertEqual(json.loads(request.data)['tools'],[{'google_search':{}}])
        self.assertNotIn('confidence',result)
        self.assertNotIn('test-key-not-secret',request.full_url)

    def test_primary_classifier_invalid_label_and_provider_failure_produce_no_label(self):
        value={'claim':CLAIM,'assessments':[],'label':'Maybe','primary_reason_en':'Reason','primary_reason_tl':'Dahilan'}
        with patch.object(reader,'open_provider',return_value=provider_response(value)):
            invalid=primary.classify_claim(CLAIM,[])
        self.assertEqual(invalid['status'],'invalid_response');self.assertNotIn('label',invalid)
        with patch.object(reader,'open_provider',side_effect=TimeoutError('private request')):
            failed=primary.classify_claim(CLAIM,[])
        self.assertEqual(failed['status'],'unavailable');self.assertNotIn('label',failed)
        self.assertNotIn('private request',str(failed))

    def test_primary_classifier_source_ids_preserve_original_passages(self):
        value=response_payload();value.update(label='Non-Misleading',self_reported_score=82,primary_reason_en='Same event.',primary_reason_tl='Parehong pangyayari.')
        with patch.object(reader,'open_provider',return_value=provider_response(value)) as call:
            result=primary.classify_claim(CLAIM,SOURCES,grounding=False)
        self.assertEqual(result['status'],'classified')
        self.assertEqual(result['assessments'][0]['evidence_excerpt'],ARTICLE)
        self.assertNotIn('tools',json.loads(call.call_args.args[0].data))

    def test_primary_score_requires_provider_integer_within_range(self):
        for bad in [None, -1, 101, 72.5, '90', True]:
            value={'claim':CLAIM,'assessments':[],'label':'Non-Misleading','self_reported_score':bad,'primary_reason_en':'Reason.','primary_reason_tl':'Dahilan.'}
            with self.subTest(score=bad),patch.object(reader,'_reserve',return_value=True),patch.object(reader,'open_provider',return_value=provider_response(value)):
                result=primary.classify_claim(CLAIM,[],grounding=False)
            self.assertEqual(result['status'],'invalid_response')
            self.assertNotIn('label',result)

    def test_grounding_links_come_only_from_provider_metadata_and_reject_script_urls(self):
        metadata={'groundingMetadata':{'groundingChunks':[{'web':{'uri':'javascript:alert(1)','title':'Bad'}},
                   {'web':{'uri':'https://example.org/public','title':'Actual provider source'}}]}}
        self.assertEqual(primary._grounding(metadata)['sources'],[{'url':'https://example.org/public','title':'Actual provider source'}])

    def test_disabled_reader_never_sends_a_request(self):
        with patch.object(reader.config,'GEMINI_ENABLED',False),patch.object(reader,'open_provider') as call:
            self.assertEqual(reader.assess_claim(CLAIM,SOURCES)['status'],'disabled');call.assert_not_called()

    def test_timeout_and_auth_error_are_sanitized(self):
        for error,status in [(TimeoutError('private request text'),'unavailable'),
            (HTTPError('https://generativelanguage.googleapis.com',403,'key detail',{},None),'authentication_failed')]:
            with patch.object(reader,'open_provider',side_effect=error):
                result=reader.assess_claim(CLAIM,SOURCES);self.assertEqual(result['status'],status)
                self.assertNotIn('private',str(result));self.assertNotIn('test-key',str(result))

    def test_incomplete_output_is_not_used(self):
        with patch.object(reader,'open_provider',return_value=provider_response(finish='MAX_TOKENS')):
            self.assertEqual(reader.assess_claim(CLAIM,SOURCES)['status'],'incomplete_response')

    def test_daily_budget_survives_memory_reset(self):
        with patch.object(reader.config,'GEMINI_REQUESTS_PER_DAY',1),patch.object(reader,'open_provider',return_value=provider_response()):
            self.assertEqual(reader.assess_claim(CLAIM,SOURCES)['status'],'assessed')
            reader._cache.clear();reader._minute.clear()
            self.assertEqual(reader.assess_claim(CLAIM,SOURCES)['status'],'rate_limited')

    def test_invalid_reader_result_keeps_original_model_prediction(self):
        model={'internal_label':'Misleading','public_label':'Potentially Misleading'}
        with patch.object(decision,'assess_claim',return_value={'status':'invalid_response','assessments':[]}):
            result=decision.apply_evidence(model,SOURCES,[],CLAIM)
        self.assertEqual(result['public_label'],model['public_label'])
        self.assertEqual(result['decision_source'],'screening_model')
        self.assertEqual(result['evidence_reader']['status'],'invalid_response')

    def test_changed_quantity_in_real_quote_cannot_override(self):
        assessment={'url':SOURCES[0]['url'],'relationship':'supports','reason':'Supported',
                    'reason_tl':'Sinusuportahan','evidence_excerpt':CLAIM.replace('three','four'),'decision_eligible':True}
        with patch.object(decision,'assess_claim',return_value={'status':'assessed','assessments':[assessment]}):
            result=decision.apply_evidence({'internal_label':'Misleading','public_label':'Potentially Misleading'},SOURCES,[],CLAIM)
        self.assertFalse(result['evidence_adjusted'])
        self.assertFalse(result['evidence_assessments'][0]['decision_eligible'])


if __name__=='__main__':unittest.main()
