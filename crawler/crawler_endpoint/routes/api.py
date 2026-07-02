"""Flask blueprint /api/*.

Endpoints:
- POST /api/crawl  — Search -> fetch -> extract -> save
- GET  /api/search — Proxy to SearXNG
- GET  /api/fetch  — Fetch single URL + extract
"""

from flask import Blueprint, jsonify, request

api_bp = Blueprint("api", __name__)


@api_bp.route("/crawl", methods=["POST"])
def crawl():
    """Search -> fetch -> extract -> save. Return results."""
    data = request.get_json(silent=True) or {}
    query = data.get("query", "")
    top_k = data.get("top_k", 5)
    # TODO: implement crawl pipeline
    return jsonify({
        "query": query,
        "results": [],
        "total_fetched": 0,
        "total_time_ms": 0,
    })


@api_bp.route("/search", methods=["GET"])
def search():
    """Proxy to SearXNG (format=json). Return raw URLs without fetch."""
    query = request.args.get("q", "")
    top_k = request.args.get("top_k", 10, type=int)
    # TODO: implement search proxy
    return jsonify({
        "query": query,
        "results": [],
    })


@api_bp.route("/fetch", methods=["GET"])
def fetch():
    """Fetch single URL + extract."""
    url = request.args.get("url", "")
    # TODO: implement fetch + extract
    return jsonify({
        "url": url,
        "title": None,
        "text": "",
        "text_path": "",
    })