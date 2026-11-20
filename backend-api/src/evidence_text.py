"""Remove only non-propositional transport/UI noise for evidence comparison.

The primary model and public analyzed_text retain the original submitted text.
Negation, named people, factual sentences, numbers and qualifications stay.
"""
import re

def prepare_evidence_text(text):
 text=re.sub(r'https?://[^\s<>]+',' ',text)
 text=re.sub(r'\b(?:WATCH|READ|LOOK|PANOORIN|BASAHIN)\s*:\s*(?=[.!?\s]*(?:$|[A-Z]))',' ',text)
 # Only complete courtesy sentences, never "Thank you for opening a school".
 text=re.sub(r'\bThank\s+you(?:\s+very\s+much)?(?:,?\s+(?:everybody|everyone))?\s*[.!?](?=\s|$)',' ',text,flags=re.I)
 text=re.sub(r'\b(?:Maraming\s+salamat|Salamat\s+po)\s*[.!?](?=\s|$)',' ',text,flags=re.I)
 # Adjacent comma-separated repetitions are speech disfluencies. Keep one
 # occurrence, including negations, rather than deleting the assertion.
 text=re.sub(r'\b(\w+)(?:,\s*\1\b)+',r'\1',text,flags=re.I)
 return re.sub(r'\s+',' ',text).strip()
