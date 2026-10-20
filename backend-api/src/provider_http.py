"""Fixed-provider HTTP only: reject redirects and bound response bodies."""
import json
from urllib import request
from urllib.parse import urlparse

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
