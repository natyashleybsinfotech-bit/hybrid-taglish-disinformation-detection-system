"""One bounded transport retry; metadata-only diagnostics, no prediction fallback."""
import json
import logging
import time
from urllib.error import HTTPError, URLError

class ProviderBudgetExceeded(Exception):
    pass

def _record(task, category, attempt, http_status=None):
    # Never log request URLs, headers, prompts, audio, raw errors or responses.
    logging.getLogger(__name__).warning(json.dumps({
        "event": "analysis_transport", "task": task,
        "category": category, "attempt": attempt, "http_status": http_status,
    }))

def request_json(request, *, opener, reader, reserve, timeout, task):
    deadline = time.monotonic() + timeout
    for attempt in (1, 2):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Analysis request deadline reached")
        if not reserve():
            _record(task, "local_rate_limit", attempt)
            raise ProviderBudgetExceeded()
        try:
            with opener(request, timeout=remaining) as response:
                result = reader(response)
            if attempt == 2:
                _record(task, "retry_recovered", attempt)
            return result
        except HTTPError as error:
            transient = error.code in {408, 500, 502, 503, 504}
            _record(task, "http_error", attempt, error.code)
            error.close()
            if not transient or attempt == 2 or time.monotonic() >= deadline:
                raise
        except (URLError, TimeoutError, ConnectionError):
            _record(task, "connection_or_timeout", attempt)
            if attempt == 2 or time.monotonic() >= deadline:
                raise
        except (ValueError, TypeError, KeyError, IndexError):
            _record(task, "invalid_response", attempt)
            raise
        except Exception:
            _record(task, "unexpected_error", attempt)
            raise
