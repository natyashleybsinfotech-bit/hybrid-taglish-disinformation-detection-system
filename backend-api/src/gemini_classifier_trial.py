"""Local primary Gemini classifier; no hybrid classifier dependency or fallback."""
import hashlib
import json
import re
import time
from urllib.error import HTTPError
from urllib.request import Request
from urllib.parse import urlparse

import config
try:
    from .provider_transport import request_json, ProviderBudgetExceeded
except ImportError:
    from provider_transport import request_json, ProviderBudgetExceeded
try:
    from . import gemini_evidence as reader
except ImportError:
    import gemini_evidence as reader

SYSTEM = reader._SYSTEM.replace("Do not generate URLs or numeric confidence.", "Do not generate URLs in reasons or assessments.") + '''
You are also the PRIMARY classifier. Return label Misleading or Non-Misleading
for the complete submitted text. Use supplied articles and Google Search when
enabled. If evidence is insufficient, still return your best classification but
do not claim verification; explain uncertainty. Absence of a source does not
establish falsity. Distinguish reporting an allegation from asserting it true,
satire, quotations, opinions and fiction.
Return self_reported_score, an integer 0 through 100 expressing your subjective
confidence in YOUR selected label. This is an uncalibrated self-assessment, not
measured accuracy, a verified truth probability, or evidence sufficiency. Reflect
uncertainty honestly; do not default to a fixed high score. Evidence assessments
must still use only server-owned passages and retain their original rules.
Return primary_reason_en and primary_reason_tl explaining the classification.
Explain the claim and evidence, not internal provider or model identities.
Preserve named entities that actually occur in the claim or source passages.
Each supplied source still requires an assessment; with no sources return [].
Do not invent source IDs or passage IDs from search results. Google Search
citations are separate provider metadata, not server-validated article passages.
'''
SCHEMA = json.loads(json.dumps(reader._SCHEMA))
SCHEMA['properties'].update({
    'label': {'type':'STRING','enum':['Misleading','Non-Misleading']},
    'self_reported_score': {'type':'INTEGER'},
    'primary_reason_en': {'type':'STRING'}, 'primary_reason_tl': {'type':'STRING'},
})
SCHEMA['required'] += ['label','primary_reason_en','primary_reason_tl','self_reported_score']

def _grounding(candidate):
    metadata=candidate.get('groundingMetadata',{})
    if not isinstance(metadata,dict):return {'sources':[],'search_suggestions_html':''}
    sources=[]
    for item in metadata.get('groundingChunks',[])[:10]:
        web=item.get('web',{}) if isinstance(item,dict) else {}
        url=web.get('uri','')
        try:valid=isinstance(url,str) and len(url)<5000 and urlparse(url).scheme=='https' and bool(urlparse(url).hostname) and not urlparse(url).username
        except ValueError:valid=False
        if valid and url not in {s['url'] for s in sources}:
            sources.append({'url':url,'title':str(web.get('title','Source'))[:300]})
    entry=metadata.get('searchEntryPoint',{})
    html=entry.get('renderedContent','') if isinstance(entry,dict) else ''
    return {'sources':sources,'search_suggestions_html':html if isinstance(html,str) and len(html)<=40000 else ''}

def classify_claim(claim, related_sources, *, grounding=True):
    def failure(status):return {'status':status,'provider':'google_gemini','model':config.GEMINI_MODEL}
    if not config.GEMINI_ENABLED or not config.GEMINI_API_KEY:return failure('not_configured')
    if not re.fullmatch(r'gemini-[a-z0-9.-]+',config.GEMINI_MODEL):return failure('invalid_configuration')
    if not isinstance(claim,str) or not claim.strip() or len(claim)>16000:return failure('input_too_long')
    readable=[s for s in related_sources if s.get('content_status')=='readable' and isinstance(s.get('article_text'),str) and s['article_text'].strip()]
    if len(readable)>5 or any(len(s['article_text'])>24000 for s in readable) or sum(len(s['article_text']) for s in readable)>60000:
        return failure('source_limit_exceeded')
    sources=[{'source_id':f's{i+1}','url':s['url'],'article_text':s['article_text']} for i,s in enumerate(readable)]
    for source in sources:source['passages']=reader._source_passages(source['source_id'],source['article_text'])
    wire=[{k:(reader.article_url_without_tracking(v) if k=='url' else v) for k,v in s.items() if k!='article_text'} for s in sources]
    data=json.dumps({'claim':claim,'sources':wire},ensure_ascii=False)
    cache_key=hashlib.sha256(('primary-gemini-v2-self-score'+config.GEMINI_MODEL+str(grounding)+data).encode()).hexdigest()
    with reader._lock:
        cached=reader._cache.get(cache_key)
        if cached and time.monotonic()-cached[0]<300:return {**cached[1],'cache_hit':True}
    if not reader._slot.acquire(blocking=False):return failure('busy')
    try:
        payload={'systemInstruction':{'parts':[{'text':SYSTEM}]},
                 'contents':[{'role':'user','parts':[{'text':data}]}],
                 'generationConfig':{'temperature':0,'maxOutputTokens':4000,'responseMimeType':'application/json','responseSchema':SCHEMA}}
        if grounding:payload['tools']=[{'google_search':{}}]
        request=Request(f'https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent',
                        data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','x-goog-api-key':config.GEMINI_API_KEY})
        body=request_json(request, opener=reader.open_provider, reader=reader.read_json, reserve=reader._reserve, timeout=config.GEMINI_TIMEOUT_SECONDS, task='classification')
        candidate=body.get('candidates',[{}])[0]
        if candidate.get('finishReason')!='STOP':return failure('incomplete_response')
        text=''.join(p.get('text','') for p in candidate.get('content',{}).get('parts',[]) if not p.get('thought'))
        value=json.loads(text)
        if value.get('label') not in {'Misleading','Non-Misleading'}:return failure('invalid_response')
        score = value.get('self_reported_score')
        if type(score) is not int or not 0 <= score <= 100:return failure('invalid_response')
        for key in ['primary_reason_en','primary_reason_tl']:
            if not isinstance(value.get(key),str) or not 1<=len(value[key])<=1500 or re.search(r'https?://',value[key],re.I):return failure('invalid_response')
        assessments=reader._validate_passage_payload(value,claim,sources)
        result={'status':'classified','provider':'google_gemini','model':config.GEMINI_MODEL,
                'label':value['label'],'self_reported_score':score,'reason_en':value['primary_reason_en'],'reason_tl':value['primary_reason_tl'],
                'assessments':assessments,'grounding_requested':grounding,'grounding':_grounding(candidate),'cache_hit':False}
        with reader._lock:
            if len(reader._cache)>=128:reader._cache.clear()
            reader._cache[cache_key]=(time.monotonic(),result)
        return result
    except ProviderBudgetExceeded:return failure('rate_limited')
    except HTTPError as error:
        return failure('rate_limited' if error.code==429 else 'authentication_failed' if error.code in {401,403} else 'unavailable')
    except (ValueError,TypeError,KeyError,IndexError):return failure('invalid_response')
    except Exception:return failure('unavailable')
    finally:reader._slot.release()
