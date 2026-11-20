import test from 'node:test';
import assert from 'node:assert/strict';
import {isValidScreeningResult,matchesSubmittedPost} from '../src/result_binding.js';
test('local scored results require a real model score and reject retired modes',()=>{
  const result={internal_label:'Non-Misleading',public_label:'No Misleading Information Detected',final_label:'No Misleading Information Detected',screening_mode:'model',model_score:0.1,analyzed_text:'Complete claim.',decision_source:'screening_model'};
  assert.equal(isValidScreeningResult(result),true);
  assert.equal(isValidScreeningResult({...result,screening_mode:'gemini'}),false);
  assert.equal(isValidScreeningResult({...result,model_score:null}),false);
  assert.equal(isValidScreeningResult({...result,internal_label:null}),false);
});

test('explicit caption fallback stays bound to its selected video post and never claims speech',()=>{
 const caption='The city opened three schools.';
 const result={screening_mode:'model',model_score:0.1,internal_label:'Non-Misleading',public_label:'No Misleading Information Detected',decision_source:'screening_model',input_type:'video',analyzed_text:caption,extraction_status:'caption_fallback',context:{analysis_basis:'video_caption_fallback',caption_complete:true},extraction:{caption_fallback_used:true,caption_text:caption,transcript_text:'',frame_ocr_text:''}};
 const request={text:caption,mediaChoice:'video'};
 assert.equal(matchesSubmittedPost(result,request),true);
 assert.equal(matchesSubmittedPost({...result,analyzed_text:'Different caption'},request),false);
 assert.equal(matchesSubmittedPost({...result,context:{...result.context,caption_complete:false}},request),false);
 assert.equal(matchesSubmittedPost({...result,extraction:{...result.extraction,transcript_text:'Fabricated speech'}},request),false);
});
