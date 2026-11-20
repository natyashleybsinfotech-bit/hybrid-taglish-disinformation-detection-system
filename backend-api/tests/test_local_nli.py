"""Reader contracts use controlled logits. The live model audit is separate."""
import json, sys, unittest
from pathlib import Path
from unittest.mock import Mock, patch
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'src')]
import local_nli as reader
import evidence_decision as decision

CLAIM='The city opened a new hospital in Manila.'
BODY='A new hospital began operating in Manila after the city opened it.'
MODEL={'public_label':'Potentially Misleading','internal_label':'Misleading'}

class LocalNliTests(unittest.TestCase):
 def setUp(self):
  self.setting=patch.object(reader.config,'LOCAL_NLI_ENABLED',True);self.setting.start();self.addCleanup(self.setting.stop)
 def test_premise_is_article_and_hypothesis_is_claim(self):
  pipe=Mock();pipe.tokenizer.return_value={'input_ids':[1,2,3]}
  pipe.return_value=[[{'label':'contradiction','score':.001},{'label':'neutral','score':.001},{'label':'entailment','score':.998}]]
  with patch.object(reader,'_get_pipeline',return_value=pipe):scores=reader.score_pairs([(BODY,CLAIM)])
  self.assertEqual(pipe.call_args.args[0],[{'text':BODY,'text_pair':CLAIM}])
  self.assertFalse(pipe.call_args.kwargs['truncation']);self.assertEqual(scores[0]['entailment'],.998)
 def test_long_pairs_are_rejected_before_inference_without_truncation(self):
  pipe=Mock();pipe.tokenizer.return_value={'input_ids':[1]*513}
  with patch.object(reader,'_get_pipeline',return_value=pipe),self.assertRaises(ValueError):reader.score_pairs([(BODY,CLAIM)])
  pipe.assert_not_called()
 def test_label_positions_are_not_guessed_and_invalid_scores_are_rejected(self):
  pipe=Mock();pipe.tokenizer.return_value={'input_ids':[1]}
  for output in [[{'label':'LABEL_0','score':1.0}], [{'label':'entailment','score':float('nan')},{'label':'neutral','score':0.0},{'label':'contradiction','score':0.0}]]:
   pipe.return_value=[output]
   with patch.object(reader,'_get_pipeline',return_value=pipe),self.assertRaises(ValueError):reader.score_pairs([(BODY,CLAIM)])
 def test_thresholded_support_returns_only_a_body_passage(self):
  with patch.object(reader,'score_pairs',return_value=[{'entailment':.9999,'neutral':.00005,'contradiction':.00005}]):
   relation,quote=reader.assess_relation(CLAIM,BODY)
  self.assertEqual(relation,'supports');self.assertIn(quote,BODY)
 def test_thresholded_contradiction_returns_only_a_body_passage(self):
  with patch.object(reader,'score_pairs',return_value=[{'entailment':.00005,'neutral':.00005,'contradiction':.9999}]):
   self.assertEqual(reader.assess_relation(CLAIM,BODY),('contradicts',BODY))
 def test_uncertain_neutral_unavailable_or_disabled_cannot_override(self):
  for scores in [{'entailment':.9,'neutral':.1,'contradiction':0},{'entailment':.01,'neutral':.98,'contradiction':.01}]:
   with patch.object(reader,'score_pairs',return_value=[scores]):self.assertEqual(reader.assess_relation(CLAIM,BODY)[0],'related')
  with patch.object(reader,'score_pairs',side_effect=RuntimeError('model missing')):self.assertEqual(reader.assess_relation(CLAIM,BODY)[0],'related')
  with patch.object(reader.config,'LOCAL_NLI_ENABLED',False),patch.object(reader,'score_pairs') as inference:
   self.assertEqual(reader.assess_relation(CLAIM,BODY)[0],'related');inference.assert_not_called()
 def test_quoted_hypothetical_or_reported_assertions_never_reach_nli(self):
  for body in ['"'+BODY+'"','If the city opened a hospital in Manila, patients would benefit.','A viral post claims the city opened a hospital in Manila.','Did the city open a hospital in Manila?']:
   with patch.object(reader,'score_pairs') as inference:
    self.assertEqual(reader.assess_relation(CLAIM,body)[0],'related');inference.assert_not_called()
 def test_opposing_nli_passages_are_conflicting(self):
  body='The city opened a hospital in Manila. The city did not open a hospital in Manila.'
  values=[{'entailment':.9999,'neutral':.00005,'contradiction':.00005},{'entailment':.00005,'neutral':.00005,'contradiction':.9999}]
  with patch.object(reader,'_windows',return_value=body.split('. ')[:2]),patch.object(reader,'score_pairs',return_value=values):
   self.assertEqual(reader.assess_relation(CLAIM,body)[0],'conflicting')
 def test_nli_is_only_after_literal_and_material_assertion_paths(self):
  with patch.object(reader,'assess_relation',side_effect=AssertionError('No fallback needed')):
   self.assertEqual(decision._article_relation(CLAIM,CLAIM)[0],'supports')
   self.assertEqual(decision._article_relation('The city opened three public schools in Manila.','Three public schools were opened by the city in Manila.')[0],'supports')
 def test_headline_alone_cannot_call_nli_or_become_evidence(self):
  with patch.object(reader,'assess_relation',side_effect=AssertionError('No headline inference')):
   decision._headline_has_body_corroboration(CLAIM,'City inaugurates a hospital','A discussion of municipal services.')
 def test_material_dates_people_and_quantities_still_block_semantic_support(self):
  for claim,body in [('The city opened three schools in Manila.','The city opened two schools in Manila.'),('Alina Reyes opened the center.','Marco Reyes opened the center.'),('The center opened on November 20, 2026.','The center opened on November 19, 2026.')]:
   source={'url':'https://gmanetwork.com/fixture','content_status':'readable','article_text':body}
   with patch.object(decision,'_assess_readable_claim',return_value=('supports',body)):
    result=decision.apply_evidence(MODEL,[source],[],claim)
   self.assertFalse(result['evidence_assessments'][0]['decision_eligible']);self.assertEqual(result['decision_source'],'screening_model')
 def test_fixture_calibration_and_audit_groups_are_disjoint(self):
  p=Path(__file__).with_name('fixtures')/'local_nli_pairs.jsonl'
  rows=[json.loads(line) for line in p.read_text(encoding='utf-8').splitlines()]
  self.assertEqual(len(rows),108)
  self.assertFalse({r['group'] for r in rows if r['split']=='calibration'} & {r['group'] for r in rows if r['split']=='audit'})
 def test_no_request_time_download_or_external_provider_dependencies(self):
  import inspect
  source=inspect.getsource(reader._get_pipeline)
  self.assertGreaterEqual(source.count('local_files_only=True'),2)
  self.assertNotIn('snapshot_download',source)
  self.assertTrue(reader.health()['offline_inference'])

if __name__=='__main__':unittest.main()
