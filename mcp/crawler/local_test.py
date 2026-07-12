"""Integration tests for crawler pipeline — run inside container against running server.

Usage (inside container with gunicorn on port 8000):
    python local_test.py

All tests call real endpoints and verify responses end-to-end:
- GET /api/health
- GET /api/search?q=...
- GET /api/fetch?url=...
- POST /api/crawl
"""

import os
import sys
import json
import time
import urllib.parse

import requests

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000")
TIMEOUT = int(os.environ.get("TEST_TIMEOUT", "30"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _request(method: str, path: str, **kwargs) -> requests.Response:
    """Make an HTTP request with common defaults."""
    url = urllib.parse.urljoin(BASE_URL.rstrip("/") + "/", path.lstrip("/"))
    resp = requests.request(method, url, timeout=TIMEOUT, **kwargs)
    return resp


def _check_ok(resp: requests.Response, description: str) -> None:
    """Assert HTTP 200 and valid JSON body."""
    if resp.status_code != 200:
        print(f"  FAIL [{description}] HTTP {resp.status_code}: {resp.text[:200]}")
        return False
    try:
        body = resp.json()
    except ValueError:
        print(f"  FAIL [{description}] response is not valid JSON: {resp.text[:200]}")
        return False
    return body


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_health() -> bool:
    """GET /api/health returns {"status": "ok"}."""
    print("[test] health ... ", end="", flush=True)
    resp = _request("GET", "/api/health")
    body = _check_ok(resp, "health")
    if body is False:
        return False
    if body.get("status") != "ok":
        print(f"  FAIL expected status=ok, got {body}")
        return False
    print("PASS")
    return True


def test_search() -> bool:
    """GET /api/search?q=pytest returns results list."""
    print("[test] search ... ", end="", flush=True)
    resp = _request("GET", "/api/search", params={"q": "python", "top_k": 3})
    body = _check_ok(resp, "search")
    if body is False:
        return False
    if body.get("query") != "python":
        print(f"  FAIL query mismatch, got {body.get('query')}")
        return False
    results = body.get("results", [])
    print(f"got {len(results)} results, ", end="", flush=True)
    for r in results:
        if not r.get("url"):
            print("  FAIL result missing url")
            return False
    print("PASS")
    return True


def test_search_empty_query() -> bool:
    """GET /api/search without query returns 400."""
    print("[test] search empty query ... ", end="", flush=True)
    resp = _request("GET", "/api/search")
    if resp.status_code != 400:
        print(f"  FAIL expected 400, got {resp.status_code}")
        return False
    body = resp.json()
    if "error" not in body:
        print(f"  FAIL expected error field, got {body}")
        return False
    print("PASS")
    return True


def test_fetch() -> bool:
    """GET /api/fetch?url=http://example.com returns extracted text."""
    print("[test] fetch ... ", end="", flush=True)
    resp = _request("GET", "/api/fetch", params={"url": "http://example.com"})
    body = _check_ok(resp, "fetch")
    if body is False:
        return False
    if body.get("url") != "http://example.com":
        print(f"  FAIL url mismatch, got {body.get('url')}")
        return False
    if not body.get("text"):
        print(f"  FAIL no extracted text")
        return False
    if not body.get("title"):
        print(f"  FAIL missing title, got {body.get('title')}")
        # continue — some pages may have empty title
    print("PASS")
    return True


def test_fetch_invalid_url() -> bool:
    """GET /api/fetch without url returns 400."""
    print("[test] fetch invalid ... ", end="", flush=True)
    resp = _request("GET", "/api/fetch")
    if resp.status_code != 400:
        print(f"  FAIL expected 400, got {resp.status_code}")
        return False
    print("PASS")
    return True


def test_crawl() -> bool:
    """POST /api/crawl with query runs full pipeline."""
    print("[test] crawl ... ", end="", flush=True)
    resp = _request("POST", "/api/crawl", json={"query": "python programming", "top_k": 3})
    body = _check_ok(resp, "crawl")
    if body is False:
        return False
    if body.get("query") != "python programming":
        print(f"  FAIL query mismatch, got {body.get('query')}")
        return False
    results = body.get("results", [])
    total_fetched = body.get("total_fetched", 0)
    total_time = body.get("total_time_ms", 0)
    print(f"fetched {total_fetched}/{len(results)} results in {total_time}ms, ", end="", flush=True)
    for r in results:
        if not r.get("text"):
            print(f"  FAIL result {r.get('url')} missing text")
            return False
        if not r.get("html_path"):
            print(f"  FAIL result {r.get('url')} missing html_path")
            return False
        if not r.get("text_path"):
            print(f"  FAIL result {r.get('url')} missing text_path")
            return False
    print("PASS")
    return True


def test_crawl_empty_query() -> bool:
    """POST /api/crawl without query returns 400."""
    print("[test] crawl empty query ... ", end="", flush=True)
    resp = _request("POST", "/api/crawl", json={})
    if resp.status_code != 400:
        print(f"  FAIL expected 400, got {resp.status_code}")
        return False
    print("PASS")
    return True


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

TESTS = [
    ("health", test_health),
    ("search", test_search),
    ("search_empty_query", test_search_empty_query),
    ("fetch", test_fetch),
    ("fetch_invalid_url", test_fetch_invalid_url),
    ("crawl", test_crawl),
    ("crawl_empty_query", test_crawl_empty_query),
]


def main() -> int:
    """Run all integration tests and exit with appropriate code."""
    print(f"Crawler integration tests — {BASE_URL}")
    print(f"{'=' * 50}")
    passed = 0
    failed = 0
    skipped = []

    for name, func in TESTS:
        try:
            ok = func()
        except requests.ConnectionError:
            print(f"  FAIL [{name}] connection refused — is the server running?")
            ok = False
        except requests.Timeout:
            print(f"  FAIL [{name}] request timed out ({TIMEOUT}s)")
            ok = False
        except Exception as exc:
            print(f"  FAIL [{name}] unexpected exception: {exc}")
            ok = False

        if ok:
            passed += 1
        else:
            failed += 1

    print(f"{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'=' * 50}")
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())