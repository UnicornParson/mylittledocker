"""Flask blueprint /mcp/*.

MCP API endpoint:
- POST /mcp/tools/call — Call MCP tools (search, crawl, fetch_page)
"""

from flask import Blueprint, jsonify, request

mcp_bp = Blueprint("mcp", __name__)


@mcp_bp.route("/tools/call", methods=["POST"])
def tools_call():
    """Call an MCP tool.

    Supported tools:
    - search     — Search SearXNG, no fetch
    - crawl      — Search -> fetch all results -> extract -> save
    - fetch_page — Fetch single URL -> extract -> save
    """
    data = request.get_json(silent=True) or {}
    tool = data.get("tool", "")
    inp = data.get("input", {})

    if tool == "search":
        # TODO: implement search tool
        return jsonify({
            "content": f"Search results for '{inp.get('query', '')}'",
            "artifacts": [],
            "meta": {"total_results": 0},
        })
    elif tool == "crawl":
        # TODO: implement crawl tool
        return jsonify({
            "content": f"Crawled {inp.get('top_k', 5)} pages from query '{inp.get('query', '')}'",
            "artifacts": [],
            "meta": {"total_fetched": 0, "total_time_ms": 0},
        })
    elif tool == "fetch_page":
        # TODO: implement fetch_page tool
        return jsonify({
            "content": f"Fetched page from '{inp.get('url', '')}'",
            "artifacts": [],
            "meta": {"fetch_time_ms": 0},
        })
    else:
        return jsonify({
            "error": f"Unknown tool: {tool}",
            "valid_tools": ["search", "crawl", "fetch_page"],
        }), 400