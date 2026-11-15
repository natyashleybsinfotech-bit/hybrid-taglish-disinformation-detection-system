r"""Inspect query construction and every Serper candidate without changing a verdict.

Examples (from the project root):
    .venv\Scripts\python.exe backend-api\scripts\diagnose_retrieval.py "sample claim"
    .venv\Scripts\python.exe backend-api\scripts\diagnose_retrieval.py --live "sample claim"

Live raw responses are written only under ignored tmp/. The provider key is
never included. Do not put sensitive post text on a shared command line.
Pass it through stdin with claim='-' instead.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend-api"))

from src import retrieval  # noqa: E402


def inspect_response(body: dict, claim: str) -> list[dict]:
    terms = retrieval._informative_terms(claim)
    accepted = {item["url"] for _score, item in retrieval._relevant_sources(body, terms, claim, None)}
    rows = []
    for item in body.get("organic", [])[:30]:
        url = str(item.get("link", "")).strip()
        title = str(item.get("title", "")).strip()
        host = urlparse(url).hostname or ""
        matches, title_matches, score = retrieval._relevance(item, terms)
        required = len(terms) if len(terms) <= 5 else 3
        title_required = 2 if len(terms) > 5 else 1 if len(terms) >= 3 else 0
        checks = {
            "safe_link": retrieval.safe_link(url),
            "has_title": bool(title),
            "keyword_overlap": matches >= required and title_matches >= title_required,
            "entity_date_amount_alignment": retrieval._entity_and_content_alignment(claim, item),
            "trusted_domain": retrieval._is_trusted_domain(host),
            "not_social_or_excluded": not retrieval._is_blocked_domain(host, None),
        }
        reasons = [name for name, passed in checks.items() if not passed]
        if not reasons and url not in accepted:
            reasons = ["same_publisher_lower_rank"]
        rows.append({
            "title": title, "url": url, "score": score,
            "matched_terms": matches, "required_terms": required,
            "title_matches": title_matches, "title_required": title_required,
            "accepted": url in accepted, "drop_reasons": reasons,
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("claim", help="Claim text, or '-' to read it from stdin")
    parser.add_argument("--live", action="store_true", help="Call configured Serper and save raw responses under ignored tmp/")
    args = parser.parse_args()
    claim = sys.stdin.read().strip() if args.claim == "-" else args.claim.strip()
    if not claim:
        parser.error("Claim must not be empty")
    raw = retrieval._search_query(claim)
    focused = retrieval._focused_search_query(claim)
    focused_first = retrieval._prefer_focused_first(claim)
    order = [("focused", focused), ("raw", raw)] if focused_first else [("raw", raw), ("focused", focused)]
    print("Primary strategy:", order[0][0])
    print("Search terms:", sorted(retrieval._informative_terms(claim)))
    for name, query in order:
        print(f"{name} query: {query}")
    if not args.live:
        print("Dry run only. Add --live to inspect actual provider filtering.")
        return 0
    record = {"claim": claim, "strategy": order[0][0], "attempts": []}
    for name, query in order:
        body = retrieval._serper_search(query)
        if body is None:
            print(f"{name}: provider unavailable or rejected the query")
            record["attempts"].append({"name": name, "query": query, "provider_status": "unavailable"})
            continue
        rows = inspect_response(body, claim)
        counts = Counter(reason for row in rows for reason in row["drop_reasons"])
        print(f"{name}: {len(body.get('organic', []))} organic; {sum(row['accepted'] for row in rows)} accepted")
        print("  drop reasons:", dict(counts))
        for row in rows:
            print("  ", "KEEP" if row["accepted"] else ",".join(row["drop_reasons"]), row["url"])
        record["attempts"].append({"name": name, "query": query, "raw_response": body, "candidate_checks": rows})
    destination = ROOT / "tmp" / f"retrieval-diagnostic-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Raw provider response and checks saved privately to", destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
