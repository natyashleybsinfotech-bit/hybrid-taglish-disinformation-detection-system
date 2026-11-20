"""Fixed-provider HTTP only: reject redirects and bound response bodies."""
import json
from urllib import request
from urllib.parse import urlparse, unquote_plus

class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

open_provider = request.build_opener(NoRedirect).open

def read_json(response):
    payload = response.read(2_000_001)
    if len(payload) > 2_000_000:
        raise ValueError("Provider response exceeds limit")
    body = json.loads(payload.decode("utf-8"))
    if not isinstance(body, dict):
        raise ValueError("Invalid provider response")
    return body

def safe_link(value):
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"https", "http"} and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        return False


def article_url_without_tracking(value):
    """Remove known attribution parameters, preserving raw meaningful queries.

    Do not decode/re-encode surviving parameters: IDs, signatures, ordering and
    encoded values can identify a different page. Never discard all queries.
    """
    try:
        parsed=urlparse(value)
        if parsed.scheme not in {'http','https'}:return value
        tracking={'fbclid','gclid','dclid','msclkid','igshid','mc_cid','mc_eid'}
        kept=[]
        for item in parsed.query.split('&'):
            name=unquote_plus(item.split('=',1)[0]).casefold()
            if name in tracking or name.startswith('utm_'):continue
            if item:kept.append(item)
        return parsed._replace(query='&'.join(kept),fragment='').geturl()
    except (ValueError,TypeError):
        return value
