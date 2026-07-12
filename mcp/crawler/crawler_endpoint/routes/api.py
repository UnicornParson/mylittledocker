from __future__ import annotations

import asyncio
import time
import uuid
from typing import List

from flask import Blueprint, jsonify, request, current_app

from crawler_endpoint.di import Container
from crawler_endpoint.models import CrawlResult, ManifestEntry, SearchResult
from crawler_endpoint.services.extractor import ExtractResult

api_bp = Blueprint("api", __name__)


def _get_container() -> Container:
    """Get DI container from Flask app extensions."""
    return current_app.extensions["container"]


def _generate_request_id() -> str:
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Healthcheck
# ---------------------------------------------------------------------------


@api_bp.route("/health", methods=["GET"])
def health():
    """Simple healthcheck endpoint."""
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# POST /api/crawl  —  full pipeline
# ---------------------------------------------------------------------------


@api_bp.route("/crawl", methods=["POST"])
def crawl():
    """Search -> fetch -> extract -> save. Return results."""
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    top_k = int(data.get("top_k", 5))
    request_id = _generate_request_id()

    if not query:
        return jsonify({"error": "query is required"}), 400

    container = _get_container()
    logger = container.logger
    start = time.monotonic()

    try:
        # 1. Search
        search_results: List[SearchResult] = asyncio.run(
            container.search_client.search(query, top_k=top_k)
        )
        logger.log(
            event="search",
            request_id=request_id,
            query=query,
            latency_ms=int((time.monotonic() - start) * 1000),
        )

        if not search_results:
            return jsonify({
                "query": query,
                "results": [],
                "total_fetched": 0,
                "total_time_ms": int((time.monotonic() - start) * 1000),
            })

        urls = [r.url for r in search_results]

        # 2. Fetch all
        raw_html_list = asyncio.run(container.fetch_engine.fetch_all(urls))

        # 3. Extract + save for each fetched page
        crawl_results: List[CrawlResult] = []
        total_fetched = 0

        for search_item, raw_html in zip(search_results, raw_html_list):
            if raw_html is None:
                continue

            total_fetched += 1

            # Extract
            extracted: ExtractResult = container.extractor.extract(raw_html)
            if not extracted.text:
                continue

            # Save HTML
            html_path = container.storage.save_html(search_item.url, raw_html)

            # Save text
            text_path = container.storage.save_text(search_item.url, extracted.text)

            # Build manifest entry
            entry = ManifestEntry(
                url=search_item.url,
                hash=container.storage._url_hash(search_item.url),
                title=extracted.title or search_item.title,
                fetched_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                fetch_time_ms=0,
                extracted_with="trafilatura+readability",
                text_bytes=len(extracted.text.encode("utf-8")),
            )
            container.storage.save_manifest(entry)

            crawl_results.append(CrawlResult(
                url=search_item.url,
                title=extracted.title or search_item.title,
                text=extracted.text,
                html_path=html_path,
                text_path=text_path,
                fetch_time_ms=0,
                extracted_with=entry.extracted_with,
            ))

        elapsed_ms = int((time.monotonic() - start) * 1000)

        logger.log(
            event="crawl",
            request_id=request_id,
            query=query,
            latency_ms=elapsed_ms,
        )

        return jsonify({
            "query": query,
            "results": [
                {
                    "url": r.url,
                    "title": r.title,
                    "text": r.text,
                    "html_path": r.html_path,
                    "text_path": r.text_path,
                    "fetch_time_ms": r.fetch_time_ms,
                    "extracted_with": r.extracted_with,
                }
                for r in crawl_results
            ],
            "total_fetched": total_fetched,
            "total_time_ms": elapsed_ms,
        })

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.log(
            event="crawl_error",
            request_id=request_id,
            query=query,
            latency_ms=elapsed_ms,
            error=str(exc),
        )
        current_app.logger.exception("Crawl pipeline failed for query=%s", query)
        return jsonify({
            "error": "internal server error",
            "message": f"crawl pipeline failed: {exc}",
        }), 500


# ---------------------------------------------------------------------------
# GET /api/search  —  proxy to SearXNG
# ---------------------------------------------------------------------------


@api_bp.route("/search", methods=["GET"])
def search():
    """Proxy to SearXNG (format=json). Return raw URLs without fetch."""
    query = (request.args.get("q") or "").strip()
    top_k = request.args.get("top_k", 10, type=int)
    request_id = _generate_request_id()

    if not query:
        return jsonify({"error": "q (query) is required"}), 400

    container = _get_container()
    logger = container.logger
    start = time.monotonic()

    search_results: List[SearchResult] = asyncio.run(
        container.search_client.search(query, top_k=top_k)
    )

    elapsed_ms = int((time.monotonic() - start) * 1000)

    logger.log(
        event="search",
        request_id=request_id,
        query=query,
        latency_ms=elapsed_ms,
    )

    return jsonify({
        "query": query,
        "results": [
            {
                "url": r.url,
                "title": r.title,
                "snippet": r.snippet,
                "engine": r.engine,
                "score": r.score,
            }
            for r in search_results
        ],
        "total_time_ms": elapsed_ms,
    })


# ---------------------------------------------------------------------------
# GET /api/fetch  —  fetch + extract + save single URL
# ---------------------------------------------------------------------------


@api_bp.route("/fetch", methods=["GET"])
def fetch():
    """Fetch single URL + extract + save to disk."""
    url = (request.args.get("url") or "").strip()
    request_id = _generate_request_id()

    if not url:
        return jsonify({"error": "url is required"}), 400

    container = _get_container()
    logger = container.logger
    start = time.monotonic()

    # 1. Fetch HTML
    raw_html = asyncio.run(container.fetch_engine.fetch(url))
    fetch_elapsed = int((time.monotonic() - start) * 1000)

    if raw_html is None:
        logger.log(
            event="fetch_error",
            request_id=request_id,
            url=url,
            error="failed to fetch page",
        )
        return jsonify({
            "url": url,
            "error": "failed to fetch page",
        }), 502

    # 2. Extract content
    extracted: ExtractResult = container.extractor.extract(raw_html)
    extract_elapsed = int((time.monotonic() - start) * 1000) - fetch_elapsed

    if not extracted.text:
        logger.log(
            event="extract_error",
            request_id=request_id,
            url=url,
            error="no content could be extracted",
        )
        # Save raw HTML even if extraction fails
        html_path = container.storage.save_html(url, raw_html)
        return jsonify({
            "url": url,
            "title": None,
            "text": "",
            "html_path": html_path,
            "text_path": "",
            "extracted_with": "",
        })

    # 3. Save HTML
    html_path = container.storage.save_html(url, raw_html)

    # 4. Save text
    text_path = container.storage.save_text(url, extracted.text)

    # 5. Manifest entry
    extracted_with = "trafilatura+readability"
    entry = ManifestEntry(
        url=url,
        hash=container.storage._url_hash(url),
        title=extracted.title or url,
        fetched_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        fetch_time_ms=fetch_elapsed,
        extracted_with=extracted_with,
        text_bytes=len(extracted.text.encode("utf-8")),
    )
    container.storage.save_manifest(entry)

    logger.log(
        event="fetch",
        request_id=request_id,
        url=url,
        latency_ms=int((time.monotonic() - start) * 1000),
    )

    return jsonify({
        "url": url,
        "title": extracted.title,
        "text": extracted.text,
        "html_path": html_path,
        "text_path": text_path,
        "fetch_time_ms": fetch_elapsed,
        "extract_time_ms": extract_elapsed,
        "extracted_with": extracted_with,
        "text_bytes": entry.text_bytes,
    })


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------


@api_bp.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "bad request", "message": str(error)}), 400


@api_bp.errorhandler(502)
def bad_gateway(error):
    return jsonify({"error": "bad gateway", "message": str(error)}), 502


@api_bp.errorhandler(503)
def service_unavailable(error):
    return jsonify({"error": "service unavailable", "message": str(error)}), 503


@api_bp.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "internal server error", "message": str(error)}), 500