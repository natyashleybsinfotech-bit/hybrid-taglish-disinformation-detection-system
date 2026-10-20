"""Measure deployed /analyze latency without changing server state."""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/analyze")
    parser.add_argument("--requests", type=int, default=30)
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()
    payload = json.dumps({"text": "May bagong advisory daw today, please verify the official source."}).encode()
    timings = []
    failures = []
    for _ in range(max(1, args.requests)):
        request = urllib.request.Request(args.url, data=payload, headers={"Content-Type": "application/json"})
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=args.timeout) as response:
                if response.status != 200:
                    failures.append(response.status)
                response.read()
        except Exception as exc:
            failures.append(type(exc).__name__)
        timings.append((time.perf_counter() - started) * 1000)
    ordered = sorted(timings)
    p95 = ordered[min(len(ordered) - 1, max(0, int(len(ordered) * 0.95) - 1))]
    print(json.dumps({"requests": len(timings), "failures": failures, "mean_ms": round(statistics.mean(timings), 2), "median_ms": round(statistics.median(timings), 2), "p95_ms": round(p95, 2)}, indent=2))
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
