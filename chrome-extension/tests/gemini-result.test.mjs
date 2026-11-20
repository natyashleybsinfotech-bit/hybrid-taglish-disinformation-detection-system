import test from 'node:test';
import assert from 'node:assert/strict';
import {isValidScreeningResult,aiReportedScore,matchesSubmittedPost} from '../src/result_binding.js';
test('Gemini unscored result requires an actual classifier decision',()=>{
  const result={internal_label:'Non-Misleading',public_label:'No Misleading Information Detected',final_label:'No Misleading Information Detected',screening_mode:'gemini',model_score:null,analyzed_text:'Complete claim.',decision_source:'gemini_classifier'};
  assert.equal(isValidScreeningResult(result),true);
  assert.equal(isValidScreeningResult({...result,decision_source:'screening_model'}),false);
  assert.equal(isValidScreeningResult({...result,model_score:0.99}),false);
  assert.equal(isValidScreeningResult({...result,internal_label:null}),false);
});

test('self-reported score is bounded and stays bound to its initial prediction',()=>{
 const result={screening_mode:'gemini',ai_score_kind:'self_reported_uncalibrated',ai_reported_score:74,ai_reported_label:'Potentially Misleading',public_label:'No Misleading Information Detected'};
 assert.deepEqual(aiReportedScore(result),{value:74,label:'Potentially Misleading'});
 for(const value of [null,undefined,NaN,-1,101,'74',true,74.1])assert.equal(aiReportedScore({...result,ai_reported_score:value}),null);
 assert.equal(aiReportedScore({...result,ai_score_kind:'accuracy'}),null);
 assert.equal(aiReportedScore({...result,ai_reported_label:'Maybe'}),null);
});

test('explicit caption fallback stays bound to its selected video post and never claims speech',()=>{
 const caption='The city opened three schools.';
 const result={screening_mode:'gemini',model_score:null,internal_label:'Non-Misleading',public_label:'No Misleading Information Detected',decision_source:'gemini_classifier',input_type:'video',analyzed_text:caption,extraction_status:'caption_fallback',context:{analysis_basis:'video_caption_fallback',caption_complete:true},extraction:{caption_fallback_used:true,caption_text:caption,transcript_text:'',frame_ocr_text:''}};
 const request={text:caption,mediaChoice:'video'};
 assert.equal(matchesSubmittedPost(result,request),true);
 assert.equal(matchesSubmittedPost({...result,analyzed_text:'Different caption'},request),false);
 assert.equal(matchesSubmittedPost({...result,context:{...result.context,caption_complete:false}},request),false);
 assert.equal(matchesSubmittedPost({...result,extraction:{...result.extraction,transcript_text:'Fabricated speech'}},request),false);
});
