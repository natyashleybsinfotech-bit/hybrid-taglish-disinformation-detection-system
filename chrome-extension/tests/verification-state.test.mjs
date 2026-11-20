import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {isValidScreeningResult,requireScreeningResult} from '../src/result_binding.js';
const read=name=>JSON.parse(readFileSync(new URL('./fixtures/verification-'+name.toLowerCase()+'.json',import.meta.url),'utf8'));
test('successful source-assisted results retain exactly the established two labels',()=>{
  for(const value of [read('SUPPORTED'),read('CONTRADICTED')]){
    assert.equal(isValidScreeningResult(value),true);
    assert.ok(['Potentially Misleading','No Misleading Information Detected'].includes(value.public_label));
    assert.equal(value.final_label,value.public_label);
    assert.equal(value.model_public_label,'Potentially Misleading');
  }
});
test('verification errors and a fabricated third classification cannot render as a successful prediction',()=>{
  const value=read('SUPPORTED');
  for(const invalid of [{detail:'No prediction was produced.'},
    {...value,internal_label:null,public_label:'Verification incomplete',final_label:'Verification incomplete'},
    {...value,internal_label:null,public_label:null,final_label:null}]){
    assert.equal(isValidScreeningResult(invalid),false);
    assert.throws(()=>requireScreeningResult(invalid));
  }
});
