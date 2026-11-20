"""Same-page article layouts and publisher-provided JSON hydration.

No scripts are executed. Body candidates must belong to the requested canonical
page, match a unique displayed headline, and have an explicit article scope.
"""
from html.parser import HTMLParser
import json
import re
from urllib.parse import urlparse, unquote

_VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
_BODY=re.compile(r'(?:^|[\s_-])(?:article|story|post|entry)[_-](?:body|content|text)(?:$|[\s_-])',re.I)
_CHROME=re.compile(r'(?:^|[\s_-])(?:related|recommendations?|advert(?:isement)?|sidebar|promo|newsletter|most-read|trending|comments?|share|social)(?:$|[\s_-])',re.I)

def _hidden(tag,attrs):
 markers=' '.join(str(attrs.get(k,'')) for k in ['class','id','role','aria-label'])
 style=str(attrs.get('style','')).replace(' ','').lower()
 return (tag in {'script','style','nav','footer','aside','form','button','noscript'}
         or 'hidden' in attrs or attrs.get('aria-hidden')=='true'
         or 'display:none' in style or 'visibility:hidden' in style
         or bool(_CHROME.search(markers)))

def _title(value):return ' '.join(re.findall(r'[^\W_]+',str(value).casefold()))

def _same_title(displayed,metadata):
 if _title(displayed)==_title(metadata):return True
 return any(_title(displayed)==_title(part) for part in re.split(r'\s+[|–—]\s+|\s+-\s+',metadata))

def _identity(value):
 try:
  p=urlparse(value)
  if p.scheme!='https' or not p.hostname or p.username or p.password:return None
  # Query identity is preserved. Attribution cleanup occurs before this parser.
  return p.hostname.casefold().removeprefix('www.'),unquote(p.path).rstrip('/'),p.query
 except (TypeError,ValueError):return None


class ScopedBodyText(HTMLParser):
 """Preserve prose in p/div blocks, including a lead outside a p element."""
 def __init__(self):super().__init__();self.stack=[];self.buffer=[];self.paragraphs=[]
 def flush(self):
  text=' '.join(' '.join(self.buffer).split());self.buffer=[]
  if len(text)>=35 and not re.match(r'^(?:read more|related stor(?:y|ies)|subscribe|sign up|advertisement)\b',text,re.I):self.paragraphs.append(text)
 def handle_starttag(self,tag,attrs):
  hidden=_hidden(tag,dict(attrs)) or tag in {'h1','h2','h3','h4','h5','h6','title','time'} or any(h for _,h in self.stack)
  if tag in {'p','div','section','figcaption','blockquote','li','br'}:self.flush()
  if tag not in _VOID:self.stack.append((tag,hidden))
 def handle_endtag(self,tag):
  if tag in {'p','div','section','figcaption','blockquote','li'}:self.flush()
  index=next((i for i in range(len(self.stack)-1,-1,-1) if self.stack[i][0]==tag),None)
  if index is not None:del self.stack[index:]
 def handle_data(self,data):
  if not any(h for _,h in self.stack):self.buffer.append(data)
 def handle_startendtag(self,tag,attrs):
  self.handle_starttag(tag,attrs)
  if tag not in _VOID:self.handle_endtag(tag)
 def text(self):self.flush();return '\n'.join(dict.fromkeys(self.paragraphs))


class SamePageArticleParser(HTMLParser):
 def __init__(self):
  super().__init__();self.stack=[];self.scopes=[];self.h1=[];self.heading=[]
  self.og_title='';self.document_title=[];self.identities=[];self.og_type=''
  self.json_blocks=[];self.schema_blocks=[];self.script=None;self.script_kind=None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='meta':
   if a.get('property')=='og:title':self.og_title=a.get('content','')
   if a.get('property')=='og:url':self.identities.append(a.get('content',''))
   if a.get('property')=='og:type':self.og_type=a.get('content','')
  if tag=='link' and 'canonical' in a.get('rel','').split():self.identities.append(a.get('href',''))
  for scope in self.scopes:
   if not scope['closed']:scope['html'].append(self.get_starttag_text())
  hidden=_hidden(tag,a) or any(h for _,h in self.stack)
  if tag=='h1' and not hidden:self.heading=[]
  marker=bool(_BODY.search(' '.join(str(a.get(k,'')) for k in ['class','id','data-testid']))) or a.get('itemprop')=='articleBody'
  if not hidden and (tag=='article' or marker):self.scopes.append({'depth':len(self.stack),'html':[],'closed':False,'explicit':marker,'headings':[]})
  if tag=='script' and a.get('type') in {'application/json','application/ld+json'} and len(self.json_blocks)+len(self.schema_blocks)<24:self.script=[];self.script_kind=a.get('type')
  if tag not in _VOID:self.stack.append((tag,hidden))
 def handle_data(self,data):
  if self.script is not None:self.script.append(data)
  for scope in self.scopes:
   if not scope['closed']:scope['html'].append(data.replace('&','&amp;').replace('<','&lt;'))
  if any(h for _,h in self.stack):return
  tags={tag for tag,_ in self.stack}
  if 'h1' in tags:self.heading.append(data)
  if 'title' in tags:self.document_title.append(data)
 def handle_endtag(self,tag):
  index=next((i for i in range(len(self.stack)-1,-1,-1) if self.stack[i][0]==tag),None)
  if tag=='h1' and self.heading:
   heading=' '.join(' '.join(self.heading).split());self.h1.append(heading);self.heading=[]
   for scope in self.scopes:
    if not scope['closed']:scope['headings'].append(heading)
  for scope in self.scopes:
   if scope['closed']:continue
   if index is not None and index<=scope['depth']:scope['closed']=True
   else:scope['html'].append('</'+tag+'>')
  if tag=='script' and self.script is not None:
   (self.schema_blocks if self.script_kind=='application/ld+json' else self.json_blocks).append(''.join(self.script));self.script=None
  if index is not None:del self.stack[index:]
 def handle_startendtag(self,tag,attrs):
  self.handle_starttag(tag,attrs)
  if tag not in _VOID:self.handle_endtag(tag)
 def article(self,requested_url):
  target=_identity(requested_url);title=self.og_title or ' '.join(self.document_title)
  if target is None or not self.identities or any(_identity(v)!=target for v in self.identities):return None
  heads={h for h in self.h1 if _same_title(h,title)}
  if not title or len(heads)!=1:return None
  headline=heads.pop()
  # Publisher JSON can contain the body before React renders its paragraphs.
  # Match the displayed title and canonical page, not a related-card description.
  count=0
  def objects(root,depth=0):
   nonlocal count
   count+=1
   if count>15_000 or depth>24:return
   if isinstance(root,dict):
    yield root
    for value in root.values():yield from objects(value,depth+1)
   elif isinstance(root,list):
    for value in root[:500]:yield from objects(value,depth+1)
  schema_verified=False
  for block in self.schema_blocks:
   try:document=json.loads(block)
   except (ValueError,RecursionError):continue
   for item in objects(document):
    kinds=item.get('@type',[]);kinds=kinds if isinstance(kinds,list) else [kinds]
    page=item.get('mainEntityOfPage');page=page.get('@id') or page.get('url') if isinstance(page,dict) else page
    identities={value for value in [_identity(item.get('url')),_identity(item.get('@id')),_identity(page)] if value is not None}
    # Some publisher NewsArticle metadata omits url/mainEntityOfPage. In that
    # case require two matching page-level identities plus a dated article;
    # an explicitly different schema URL is never ignored.
    bound=(target in identities) if identities else (len(self.identities)>=2 and bool(re.match(r'^20\d{2}-\d{2}-\d{2}T',str(item.get('datePublished','')))))
    if (any(k in {'Article','NewsArticle','ReportageNewsArticle'} for k in kinds if isinstance(k,str))
        and isinstance(item.get('headline'),str) and _same_title(headline,item['headline'])
        and bound):schema_verified=True
  if self.og_type and self.og_type.casefold() not in {'article','newsarticle'} and not schema_verified:return None
  explicit_bodies=set();article_bodies=set()
  for scope in self.scopes:
   if not scope['closed'] or (not scope['explicit'] and not any(_same_title(headline,h) for h in scope['headings'])):continue
   parser=ScopedBodyText();parser.feed(''.join(scope['html']));body=parser.text()
   if 80<=len(body)<=200_000:(explicit_bodies if scope['explicit'] else article_bodies).add(body)
  bodies=explicit_bodies or article_bodies
  for block in self.json_blocks:
   try:document=json.loads(block)
   except (ValueError,RecursionError):continue
   for item in objects(document):
    raw=item.get('body_html');heading=item.get('headline')
    if not isinstance(raw,str) or not (80<=len(raw)<=200_000) or not isinstance(heading,str) or not _same_title(headline,heading):continue
    if not schema_verified or item.get('pubstatus','usable')!='usable' or item.get('type','text') not in {'text','article','story'}:continue
    page=item.get('canonical_url') or item.get('url')
    if page is not None and _identity(page)!=target:continue
    parser=ScopedBodyText();parser.feed(raw);body=parser.text()
    if 80<=len(body)<=200_000:bodies.add(body)
  if len(bodies)!=1:return None
  return {'content_status':'readable','title':headline,'article_text':bodies.pop(),'extraction_method':'same_page_article_scope'}
