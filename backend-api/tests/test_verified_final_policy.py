"""Offline decision-policy fixtures. No browser, database, provider or factual-accuracy benchmark."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / 'src')]
import app as application
import evidence_decision
import gemini_evidence
from model_runtime import Prediction, FEATURE_NAMES
from fastapi import HTTPException


CLAIM = 'Manila is the capital of the Philippines.'


def sources():
    # Synthetic article fixtures; these URLs are deliberately not real reports.
    return [
        {'url':'https://www.gmanetwork.com/news/fixture-capital', 'content_status':'readable',
         'article_text':'Manila is the capital of the Philippines. The national administration maintains important government offices in the city alongside its historic districts.'},
        {'url':'https://www.rappler.com/fixture-capital', 'content_status':'readable',
         'article_text':'A city profile identifies Manila as the capital of the Philippines. It explains the surrounding metropolitan region and describes the historical development of local institutions.'},
    ]


def assessment(claim, articles, relation='supports'):
    owned=[];rows=[]
    for i,source in enumerate(articles,1):
        sid=f's{i}'
        passages=gemini_evidence._source_passages(sid,source['article_text'])
        owned.append({'source_id':sid,'url':source['url'],'article_text':source['article_text'],'passages':passages})
        rows.append({'source_id':sid,'relationship':relation,
                     'passage_ids':[passages[0]['passage_id']] if relation in {'supports','contradicts'} else [],
                     'reason_en':'The supplied passage addresses the submitted claim.',
                     'reason_tl':'Tinutukoy ng ibinigay na sipi ang isinumiteng claim.'})
    checked=gemini_evidence._validate_passage_payload({'claim':claim,'assessments':rows},claim,owned)
    return {'status':'assessed','assessments':checked,'provider':'fixture_reader'}


class VerifiedFinalPolicyTests(unittest.TestCase):
    def setUp(self):
        self.settings=patch.multiple(application.config,SCREENING_MODE='model',MODEL_AUTHORITATIVE=False,
                                    GEMINI_ENABLED=True,EVIDENCE_POLICY='strict')
        self.settings.start();self.addCleanup(self.settings.stop)
        self.model=patch.object(application,'classify',return_value=self.prediction('Misleading',.999999))
        self.classifier=self.model.start();self.addCleanup(self.model.stop)
        for owner,name,value in [(application.database,'is_configured',False),
                                 (application,'_lookup_readable_sources',{'retrieval_status':'no_results','related_sources':[]}),
                                 (evidence_decision,'assess_claim',{'status':'no_readable_sources','assessments':[]})]:
            p=patch.object(owner,name,return_value=value);p.start();self.addCleanup(p.stop)
        self.lookup=application._lookup_readable_sources
        self.reader=evidence_decision.assess_claim
        self.llm=patch.object(application,'classify_claim',side_effect=AssertionError('Primary model must remain DistilBERT'))
        self.llm.start();self.addCleanup(self.llm.stop)

    def prediction(self,label,score):
        return Prediction(internal_label=label,public_label='Potentially Misleading' if label=='Misleading' else 'No Misleading Information Detected',
            confidence=score if label=='Misleading' else 1-score,model_score=score,predicted_class=int(label=='Misleading'),
            model_status='ready',model_name='Fixture DistilBERT + LR',model_version='fixture',
            linguistic_indicators=[{'name':name,'value':0.0} for name in FEATURE_NAMES])

    def run_claim(self,claim=CLAIM,retrieve=True):
        return application.analyze(application.ScreenRequest(text=claim,retrieve_sources=retrieve))

    def with_sources(self,claim=CLAIM,relation='supports',articles=None):
        articles=articles if articles is not None else sources()
        self.lookup.return_value={'retrieval_status':'available','related_sources':articles}
        self.reader.return_value=assessment(claim,articles,relation)
        return self.run_claim(claim)

    def assert_model_retained(self,value):
        self.assertEqual(value['public_label'],value['model_public_label'])
        self.assertIn(value['public_label'],{'Potentially Misleading','No Misleading Information Detected'})
        self.assertEqual(value['decision_source'],'screening_model')
        self.assertEqual(value['verification_status'],'not_verified')
        self.assertFalse(value['evidence_adjusted'])
        self.assertEqual(len(value['linguistic_indicators']),7)

    def test_no_sources_and_search_off_keep_the_actual_binary_model_prediction(self):
        self.assert_model_retained(self.run_claim())
        self.assert_model_retained(self.run_claim(retrieve=False))

    def test_validated_independent_support_can_correct_a_model_false_positive(self):
        value=self.with_sources()
        self.assertEqual(value['public_label'],'No Misleading Information Detected')
        self.assertEqual(value['model_public_label'],'Potentially Misleading')
        self.assertEqual(value['model_score'],.999999)
        self.assertEqual(value['decision_source'],'verified_evidence')
        self.assertEqual(len(value['evidence_urls']),2)
        self.assertTrue(all(s['evidence_excerpt'] and s['used_for_decision'] for s in value['related_sources']))
        self.classifier.assert_called_once_with(CLAIM)

    def test_validated_contradictions_preserve_a_supported_warning(self):
        value=self.with_sources('Tokyo is the capital of the Philippines.',relation='contradicts')
        self.assertEqual(value['public_label'],'Potentially Misleading')
        self.assertEqual(value['evidence_relationship'],'contradicts')
        self.assertEqual(value['decision_source'],'verified_evidence')

    def test_unrelated_articles_and_one_publisher_do_not_fabricate_an_override(self):
        self.assert_model_retained(self.with_sources(relation='related'))
        self.assert_model_retained(self.with_sources(articles=sources()[:1]))

    def test_syndicated_bodies_do_not_count_as_independent_evidence(self):
        articles=sources();articles[1]['article_text']=articles[0]['article_text']
        self.assert_model_retained(self.with_sources(articles=articles))

    def test_evidence_provider_errors_keep_the_valid_classifier_result(self):
        articles=sources();self.lookup.return_value={'retrieval_status':'available','related_sources':articles}
        for status in ['busy','rate_limited','unavailable','authentication_failed','invalid_response','incomplete_response']:
            with self.subTest(status=status):
                self.reader.return_value={'status':status,'assessments':[]}
                self.assert_model_retained(self.run_claim())

    def test_material_date_mismatch_cannot_force_a_supported_label(self):
        claim='The airport opened on November 20, 2026.'
        articles=sources()
        for s in articles:s['article_text']='The airport opened on November 19, 2026. '+s['article_text']
        value=self.with_sources(claim,articles=articles)
        self.assert_model_retained(value)
        self.assertTrue(any('event_date' in s['validation_issues'] for s in value['related_sources']))

    def test_unknown_passage_reference_cannot_supply_proof(self):
        source=sources()[0];owned={'source_id':'s1',**source,'passages':gemini_evidence._source_passages('s1',source['article_text'])}
        with self.assertRaises(ValueError):
            gemini_evidence._validate_passage_payload({'claim':CLAIM,'assessments':[{'source_id':'s1','relationship':'supports','passage_ids':['invented'],'reason_en':'test','reason_tl':'test'}]},CLAIM,[owned])

    def test_negative_model_prediction_is_not_turned_into_misleading_by_missing_sources(self):
        self.classifier.return_value=self.prediction('Non-Misleading',.1)
        value=self.run_claim()
        self.assert_model_retained(value)
        self.assertEqual(value['public_label'],'No Misleading Information Detected')
        self.assertEqual(value['model_score'],.1)

    def test_pure_model_research_mode_explicitly_bypasses_evidence(self):
        with patch.object(application.config,'MODEL_AUTHORITATIVE',True),patch.object(application,'apply_evidence',side_effect=AssertionError('Raw model mode')):
            value=self.run_claim()
        self.assert_model_retained(value)

    def test_caption_video_agreement_does_not_automatically_mean_the_claim_is_true(self):
        value=application.analyze(application.ScreenRequest(text=CLAIM,context={'caption_video_agreement':True},retrieve_sources=False))
        self.assert_model_retained(value)
        self.assertEqual(value['public_label'],'Potentially Misleading')


if __name__=='__main__':unittest.main()
