"""Literal quote/report structure, not a topical truth rule or publisher bypass."""
import re
try:
 from .evidence_text import prepare_evidence_text
except ImportError:
 from evidence_text import prepare_evidence_text

_REPORT=r'(?:said|says|stated|announced|confirmed|explained|reported|added|told)'
_NEG={'no','not','never','hindi','walang','wala','neither'}
_FUNCTION={'a','an','the','there','is','are','was','were','be','been','being','we','they','i','you','he','she','it','that','this','on','at','in','to','of','for','and','or','but','as','by','do','does','did','doing','will','would','have','has','had','very','much','everybody','everyone','thank'}

def words(value):return re.findall(r'[^\W_]+',value.casefold())

def split_statements(text):
 text=re.sub(r'\b(?:Mr|Mrs|Ms|Dr|Jr|Sr|Atty|Sen|Rep|Gov|Pres|Gen|Sec|Engr)\.',lambda m:m.group()[:-1]+'\ue000',text,flags=re.I)
 text=re.sub(r'\b(?:[A-Za-z]\.){2,}',lambda m:m.group().replace('.','\ue000'),text)
 out=[];start=0;quote=None
 pairs={'“':'”','‘':'’','"':'"',"'":"'"}
 for i,c in enumerate(text):
  if quote:
   if c==quote and not (c in {"'",'’'} and i+1<len(text) and text[i+1].isalnum()):quote=None
  elif c in pairs and not (c=="'" and i and text[i-1].isalnum()):quote=pairs[c]
  if quote is None and c in '.!?\n' and (i+1==len(text) or text[i+1].isspace() or text[i+1].isupper()):
   item=text[start:i+1].strip().replace('\ue000','.')
   if item:out.append(item)
   start=i+1
 item=text[start:].strip().replace('\ue000','.')
 if item:out.append(item)
 return out

def is_english_report(text):
 """Restricted to explicit English attribution syntax; other claims use base NLI."""
 normalized=words(text)
 return (bool(re.search(r'\b'+_REPORT+r'\b',text,re.I))
         and bool(re.search(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)',text))
         and len(set(normalized)&{'the','is','are','was','were','not','of','during','that','would','will','in','to'})>=3
         and not set(normalized)&{'ang','ng','mga','nang','si','sina','ay','hindi','daw','raw'})

def split_banner(text):
 """A quoted title remains a required quote, not a discarded factual assertion."""
 m=re.match(r'''^[\s]*["'“‘]([^"'”’]{5,300})["'”’]\s+(.+)$''',text,re.S)
 if m and is_english_report(m.group(2)):return m.group(1),m.group(2)
 return None,text

def source_quotes(body):
 # Prefer quotation marks, not apostrophes inside names or possessives.
 return [(m.group(1),m.start(),m.end()) for m in re.finditer(r'[“"]([^”"]{5,1400})[”"]',body)]

def _speaker_after(text):
 m=re.match(r'^[\s,]*((?:(?:[A-Z][\w.-]*|de|del|dela|of|the)\s+){0,6}[A-Z][\w.-]*)\s+'+_REPORT+r'\b',text)
 return m.group(1) if m else None

def _speaker_before(text):
 # A preceding full stop bounds unrelated speakers except title abbreviations.
 m=re.search(r'((?:(?:[A-Z][\w.-]*|de|del|dela|of|the)\s+){0,6}[A-Z][\w.-]*)\s+'+_REPORT+r'\s*[,\:]?\s*$',text)
 return m.group(1) if m else None

def quote_support(quote,body,*,speaker=None):
 target=words(quote)
 if len(target)<3:return None
 for actual,start,end in source_quotes(body):
  tokens=words(actual)
  match=any(tokens[i:i+len(target)]==target for i in range(len(tokens)-len(target)+1))
  if not match:continue
  after=body[end:end+160];before=body[max(0,start-160):start]
  owner=_speaker_after(after) or _speaker_before(before)
  if speaker:
   wanted=set(words(speaker))-{'president','mr','mrs','jr','sr','dr'}
   owned=set(words(owner or ''))-{'president','mr','mrs','jr','sr','dr'}
   if not wanted or not owned:continue
   if len(wanted)>1 and len(owned)>1:
    if not wanted<=owned:continue
   elif not (wanted & owned):continue
  elif not owner:continue
  # Return only a literal body substring, including its source attribution.
  stop=body.find('\n',end)
  return body[start:(stop if stop!=-1 else min(len(body),end+160))]
 return None

def attributed_quote_relation(claim,body):
 m=re.match(r'^\s*[“"]([^”"]+)[”"]\s*[,\s]*(.*?)\s*$',claim,re.S)
 if not m:return None
 speaker=_speaker_after(m.group(2))
 if speaker:
  passage=quote_support(m.group(1),body,speaker=speaker)
  if passage:return 'supports',passage
 return None

def speech_echo_support(speech,body):
 """Only deictic quote echoes, after the complete caption has been supported.

    Any new actor, number or unmatched topic word makes this fail. Negation is
    checked for each meaningful token rather than erased as a stopword.
 """
 speech=prepare_evidence_text(speech)
 if not speech:return ''
 if re.search(r'\d',speech):return None
 # Proper names in transcript speech need independent evidence assessment.
 if re.search(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',speech):return None
 chunks=split_statements(speech);passages=[]
 def polarity(tokens,term):
  return {bool(set(tokens[max(0,i-5):i])&_NEG) for i,w in enumerate(tokens) if w==term}
 for chunk in chunks:
  tokens=words(chunk);terms=set(tokens)-_FUNCTION-_NEG
  if not terms:return None
  found=None
  for actual,start,end in source_quotes(body):
   candidate=words(actual)
   if not terms<=set(candidate):continue
   if not all(polarity(tokens,term)<=polarity(candidate,term) for term in terms):continue
   owner=_speaker_after(body[end:end+160]) or _speaker_before(body[max(0,start-160):start])
   if not owner:continue
   stop=body.find('\n',end);found=body[start:(stop if stop!=-1 else min(len(body),end+160))];break
  if found is None:return None
  passages.append(found)
 return '\n'.join(dict.fromkeys(passages))
