"""Offline threshold sweep; never trains or modifies the DistilBERT classifier."""
import argparse, hashlib, json, sys, time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(BASE),str(BASE/'src')]
import local_nli

def summary(rows, cutoffs):
 labels=['supports','contradicts','related']
 confusion={actual:{prediction:0 for prediction in labels} for actual in labels}
 for row in rows:
  scores=row['scores'];winner=max(scores,key=scores.get)
  predicted={'entailment':'supports','contradiction':'contradicts'}.get(winner,'related') if winner in cutoffs and scores[winner]>=cutoffs[winner] else 'related'
  confusion[row['relationship']][predicted]+=1
 return {'n':len(rows),'confusion':confusion,'accuracy':sum(confusion[k][k] for k in labels)/len(rows)}

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--scores',type=Path);args=parser.parse_args()
 import torch;torch.set_num_threads(4)
 source=BASE/'tests/fixtures/local_nli_pairs.jsonl'
 rows=[json.loads(line) for line in source.read_text(encoding='utf-8').splitlines() if line]
 assert not ({r['group'] for r in rows if r['split']=='calibration'} & {r['group'] for r in rows if r['split']=='audit'})
 started=time.perf_counter()
 if args.scores:
  saved=json.loads(args.scores.read_text(encoding='utf-8'))
  assert saved['fixture_sha256']==hashlib.sha256(source.read_bytes()).hexdigest()
  assert saved['model_revision']==local_nli._MODEL_REVISION
  scores={r['id']:r['scores'] for r in saved['rows']}
  for row in rows:row['scores']=scores[row['id']]
 else:
  for start in range(0,len(rows),12):
   batch=rows[start:start+12]
   values=local_nli.score_pairs([(r['article_excerpt'],r['claim']) for r in batch])
   for row,score in zip(batch,values):row['scores']=score
   print(f'Local NLI scored {min(start+12,len(rows))}/{len(rows)} pairs',flush=True)
 calibration=[r for r in rows if r['split']=='calibration'];audit=[r for r in rows if r['split']=='audit']
 cutoffs={};sweeps={}
 for label,relationship in [('entailment','supports'),('contradiction','contradicts')]:
  sweep=[]
  for threshold in [i/200 for i in range(140,200)]+[0.996,0.997,0.998,0.999,0.9995,0.9999]:
   accepted=[r for r in calibration if max(r['scores'],key=r['scores'].get)==label and r['scores'][label]>=threshold]
   tp=sum(r['relationship']==relationship for r in accepted);fp=len(accepted)-tp
   sweep.append({'threshold':threshold,'tp':tp,'fp':fp,'precision':tp/len(accepted) if accepted else None})
  safe=[r for r in sweep if r['tp']>0 and r['fp']==0]
  best=max(safe,key=lambda r:(r['tp'],r['threshold'])) if safe else {'threshold':1.0}
  cutoffs[label]=best['threshold'];sweeps[label]=sweep
 report={'purpose':'Small authored synthetic calibration, not factual accuracy validation or a representative Taglish benchmark',
         'model_revision':local_nli._MODEL_REVISION,'fixture_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
         'selection_rule':'Maximize accepted correct calibration relations with zero wrong accepted relations; tie chooses higher threshold. Audit is never used for selection.',
         'thresholds':cutoffs,'calibration':summary(calibration,cutoffs),'audit':summary(audit,cutoffs),
         'audit_by_language':{lang:summary([r for r in audit if r['language']==lang],cutoffs) for lang in ['en','tl','taglish']},
         'elapsed_seconds':round(time.perf_counter()-started,3),'sweep':sweeps,'rows':rows}
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k not in {'sweep','rows'}},indent=2),flush=True)

if __name__=='__main__':main()
