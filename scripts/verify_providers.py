"""Actual configured provider calls using public, non-participant queries."""
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend-api'),str(ROOT/'backend-api/src')]
import config
from retrieval import retrieve_related_sources
from fact_check import search_fact_checks

report={}
for name, enabled, key, call in (
    ('serper',config.SERPER_ENABLED,config.SERPER_API_KEY,lambda:retrieve_related_sources('PAGASA official weather advisories Philippines')),
    ('google_fact_check',config.GOOGLE_FACT_CHECK_ENABLED,config.GOOGLE_FACT_CHECK_API_KEY,lambda:search_fact_checks('Philippines typhoon weather advisory')),
):
    start=time.perf_counter();result=call();elapsed=(time.perf_counter()-start)*1000
    report[name]={'enabled':enabled,'credential_present':bool(key),'status':result.get('retrieval_status',result.get('status')),
                  'results':len(result.get('related_sources',result.get('matches',[]))),'latency_ms':round(elapsed,3),
                  'live_request_attempted':bool(enabled and key)}
(ROOT/'docs/PROVIDER-VERIFICATION.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
