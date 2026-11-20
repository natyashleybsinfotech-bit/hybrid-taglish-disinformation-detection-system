import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'src')]
import evidence_decision as e
from evidence_text import prepare_evidence_text
from reported_claims import split_statements,is_english_report,attributed_quote_relation,speech_echo_support

MODEL={'internal_label':'Misleading','public_label':'Potentially Misleading'}
CLAIM='The city opened three public schools in Manila on Monday.'
def sources(body):return [{'url':'https://gmanetwork.com/fixture','content_status':'readable','article_text':body+' The local authority held a meeting discussing public budgets, staffing and education.'},{'url':'https://rappler.com/fixture','content_status':'readable','article_text':body+' Residents attended the ceremony and toured the buildings with teachers and students.'}]

class EvidenceTextTests(unittest.TestCase):
 def test_links_and_complete_greetings_cannot_add_material_numbers_or_claims(self):
  text=CLAIM+' WATCH: https://example.com/999 Thank you very much. Thank you very much, everybody. Thank you.'
  self.assertEqual(prepare_evidence_text(text),CLAIM)
  with patch.object(e.config,'EVIDENCE_POLICY','strict'):
   value=e.apply_evidence(MODEL,sources(CLAIM),[],text)
  self.assertEqual(value['public_label'],'No Misleading Information Detected')
 def test_polite_factual_sentences_and_all_negation_are_retained(self):
  text='Thank you for opening three schools. No, no, the school did not open. Watch: The school is closed.'
  cleaned=prepare_evidence_text(text)
  self.assertIn('Thank you for opening three schools.',cleaned);self.assertIn('did not open',cleaned);self.assertIn('school is closed',cleaned)
 def test_us_and_name_abbreviations_and_quoted_periods_do_not_split_entities(self):
  text='President Ana Cruz Jr. said the U.S. office had opened. "No, not today. We will return," Cruz said.'
  parts=split_statements(text);self.assertEqual(len(parts),2);self.assertIn('U.S.',parts[0]);self.assertIn('not today. We',parts[1])
 def test_concatenated_publisher_paragraphs_preserve_sentence_boundaries(self):
  self.assertEqual(split_statements('The office opened.The council will coordinate policy.'),['The office opened.','The council will coordinate policy.'])
 def test_extra_unsupported_factual_sentence_is_not_dropped_with_greetings(self):
  value=e.apply_evidence(MODEL,sources(CLAIM),[],CLAIM+' All flights have been canceled. Thank you.')
  self.assertEqual(value['decision_source'],'screening_model')
 def test_optional_middle_initial_does_not_allow_a_different_person_or_suffix(self):
  self.assertTrue(e._people_preserved('President Ana Cruz Jr. spoke.','President Ana B. Cruz Jr. spoke.'))
  self.assertFalse(e._people_preserved('President Ana Cruz Jr. spoke.','President Bea Cruz Jr. spoke.'))
  self.assertFalse(e._people_preserved('President Ana Cruz Jr. spoke.','President Ana Cruz Sr. spoke.'))
 def test_explicit_quotes_require_the_correct_source_attribution(self):
  quote='"The office will remain open tomorrow," Ana Cruz said.'
  good='“The office will remain open tomorrow,” Ana Cruz said.'
  self.assertEqual(attributed_quote_relation(quote,good)[0],'supports')
  self.assertIsNone(attributed_quote_relation(quote,good.replace('Ana Cruz','Bea Cruz')))
 def test_short_quote_echo_checks_each_negation_and_cannot_verify_new_facts(self):
  body='“There is no agreement. We are not discussing that on this visit,” Mayor Ana Cruz said.'
  self.assertIsNotNone(speech_echo_support('There is no agreement. We are not discussing that on this visit. Thank you.',body))
  for speech in ['There is an agreement.','We are discussing that on this visit.','There are two agreements.','Governor Bea Ramos approved the agreement.','The hospital has closed.']:
   self.assertIsNone(speech_echo_support(speech,body))
 def test_reported_support_policy_is_not_applied_to_plain_or_taglish_assertions(self):
  self.assertTrue(is_english_report('President Ana Cruz said the city would not close the office.'))
  self.assertFalse(is_english_report('The city opened three schools in Manila.'))
  self.assertFalse(is_english_report('Ana Cruz said hindi raw nagbukas ang school.'))
 def test_wrong_number_and_date_still_block_a_reported_support(self):
  for claim,body in [('Mayor Ana Cruz said three schools opened in Manila.','Mayor Ana Cruz said two schools opened in Manila.'),('Mayor Ana Cruz said the office opened on November 20, 2026.','Mayor Ana Cruz said the office opened on November 19, 2026.')]:
   with patch.object(e,'_assess_readable_claim',return_value=('supports',body)):
    value=e.apply_evidence(MODEL,sources(body),[],claim)
   self.assertFalse(any(s['decision_eligible'] for s in value['evidence_assessments']))

if __name__=='__main__':unittest.main()
