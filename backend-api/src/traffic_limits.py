"""Bound public screening and login traffic for the single-process deployment."""

import time
from collections import OrderedDict

from starlette.responses import JSONResponse


class TrafficLimits:
    def __init__(self, app, *, enabled=True, max_clients=10000, concurrency=2):
        self.app = app
        self.enabled = enabled
        self.max_clients = max_clients
        self.concurrency = concurrency
        self.active = 0
        self.windows = OrderedDict()

    async def __call__(self, scope, receive, send):
        if not self.enabled or scope["type"] != "http" or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        path = scope["path"]
        screening = path in {"/analyze", "/predict", "/candidates", "/analyze/image", "/analyze/video"}
        login = path == "/admin-api/login"
        if not (screening or login):
            return await self.app(scope, receive, send)
        # Uvicorn resolves the client from the trusted reverse proxy. Never parse
        # an arbitrary X-Forwarded-For header here.
        client = (scope.get("client") or ("unknown",))[0]
        key = (client, "login" if login else "screen")
        now = time.monotonic()
        start, count = self.windows.pop(key, (now, 0))
        if now - start >= 60:
            start, count = now, 0
        self.windows[key] = (start, count + 1)
        while len(self.windows) > self.max_clients:
            self.windows.popitem(last=False)
        if count >= (5 if login else 20):
            return await JSONResponse(
                {"detail": "Too many requests. Please try again shortly."},
                status_code=429, headers={"Retry-After": str(max(1, int(60 - (now - start))))},
            )(scope, receive, send)
        if screening and self.active >= self.concurrency:
            return await JSONResponse(
                {"detail": "Screening is busy. Please retry shortly."},
                status_code=503, headers={"Retry-After": "5"},
            )(scope, receive, send)
        if screening:
            self.active += 1
        try:
            await self.app(scope, receive, send)
        finally:
            if screening:
                self.active -= 1
