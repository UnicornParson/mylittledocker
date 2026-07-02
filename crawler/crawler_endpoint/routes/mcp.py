"""Flask blueprint /mcp/*.

MCP API endpoint:
- POST /mcp/tools/call — Call MCP tools (search, crawl, fetch_page)

All tools use the DI container from ``current_app.extensions["container"]``.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List

from flask import Blueprint, current_app, jsonify, request

from crawler_endpoint.models import ManifestEntry, SearchResult

mcp_bp = Blueprint("mcp", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_container():
    """Shortcut to retrieve the DI container from Flask extensions."""
    return current_app.extensions["container"]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

async def _search_tool(query: str, top_k: int = 10) -> dict:
    """Execute search via SearchClient and return structured response."""
    container = _get_container()
    results: List[SearchResult] = await container.search_client.search(query, top_k)

    lines = [f"**Результаты поиска по запросу «{query}»:**"]
    artifacts: List[Dict[str, Any]] = []

    for i, r in enumerate(results, 1):
        lines.append(f"\n{i}. [{r.title}]({r.url}) — {r.snippet}")
        artifacts.append({
            "type": "search_result",
            "url": r.url,
            "title": r.title,
            "snippet": r.snippet,
            "engine": r.engine,
            "score": r.score,
        })

    content = "\n".join(lines) if results else f"По запросу «{query}» ничего не найдено."

    return {
        "content": content,
        "artifacts": artifacts,
        "meta": {
            "total_results": len(results),
            "query": query,
            "top_k": top_k,
        },
    }


async def _fetch_page_tool(url: str) -> dict:
    """Fetch single URL → extract → save to disk.

    Returns structured MCP response with extracted content and metadata.
    """
    container = _get_container()
    start = time.monotonic()

    # 1. Fetch
    raw_html = await container.fetch_engine.fetch(url)
    if raw_html is None:
        return {
            "content": f"Не удалось загрузить страницу: {url}",
            "artifacts": [],
            "meta": {"fetch_time_ms": 0, "error": "fetch_failed"},
        }

    fetch_time_ms = int((time.monotonic() - start) * 1000)

    # 2. Extract
    extracted = container.extractor.extract(raw_html)
    text = extracted.text or ""
    title = extracted.title or ""

    # 3. Save to disk
    html_path = container.storage.save_html(url, raw_html)
    txt_path = ""
    text_bytes = 0
    if text:
        txt_path = container.storage.save_text(url, text)
        text_bytes = len(text.encode("utf-8"))

    # 4. Manifest entry
    import hashlib
    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
    manifest_entry = ManifestEntry(
        url=url,
        hash=url_hash,
        title=title,
        fetched_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        fetch_time_ms=fetch_time_ms,
        extracted_with="trafilatura/readability",
        text_bytes=text_bytes,
    )
    container.storage.save_manifest(manifest_entry)

    # 5. Log
    container.logger.log_fetch(
        url=url,
        status="success",
        fetch_time_ms=fetch_time_ms,
        text_bytes=text_bytes,
    )

    # Build response
    snippet = text[:500] + "…" if len(text) > 500 else text

    return {
        "content": (
            f"**Страница:** {title or url}\n\n"
            f"{snippet}\n\n"
            f"*Сохранено: html → {html_path}, txt → {txt_path}*"
        ),
        "artifacts": [
            {
                "type": "page",
                "url": url,
                "title": title,
                "text_length": len(text),
                "html_path": html_path,
                "text_path": txt_path,
                "fetch_time_ms": fetch_time_ms,
            }
        ],
        "meta": {
            "fetch_time_ms": fetch_time_ms,
            "text_bytes": text_bytes,
            "extracted": bool(text),
        },
    }


async def _crawl_tool(query: str, top_k: int = 5) -> dict:
    """Full pipeline: search → fetch all → extract all → save all.

    Returns aggregated MCP response with summary and per-page artifacts.
    """
    container = _get_container()
    total_start = time.monotonic()

    # 1. Search
    results: List[SearchResult] = await container.search_client.search(query, top_k)
    if not results:
        return {
            "content": f"По запросу «{query}» ничего не найдено.",
            "artifacts": [],
            "meta": {"total_fetched": 0, "total_time_ms": 0},
        }

    urls = [r.url for r in results]

    # 2. Fetch all in parallel
    html_bodies = await container.fetch_engine.fetch_all(urls)

    # 3. Extract & save
    artifacts: List[Dict[str, Any]] = []
    fetched_count = 0
    successful_count = 0
    total_text_bytes = 0

    for i, (url, result) in enumerate(zip(urls, html_bodies)):
        if result is None:
            artifacts.append({
                "type": "page",
                "url": url,
                "status": "fetch_failed",
            })
            continue

        fetched_count += 1

        # Extract
        extracted = container.extractor.extract(result)
        text = extracted.text or ""
        title = extracted.title or ""

        # Save
        html_path = container.storage.save_html(url, result)
        txt_path = ""
        text_bytes = 0
        if text:
            txt_path = container.storage.save_text(url, text)
            text_bytes = len(text.encode("utf-8"))
            total_text_bytes += text_bytes
            successful_count += 1

        # Manifest
        import hashlib
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
        manifest_entry = ManifestEntry(
            url=url,
            hash=url_hash,
            title=title,
            fetched_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            fetch_time_ms=0,  # individual fetch time not tracked per URL in batch
            extracted_with="trafilatura/readability",
            text_bytes=text_bytes,
        )
        container.storage.save_manifest(manifest_entry)

        artifacts.append({
            "type": "page",
            "url": url,
            "title": title,
            "status": "success" if text else "no_content",
            "text_length": len(text),
            "html_path": html_path,
            "text_path": txt_path,
        })

    total_time_ms = int((time.monotonic() - total_start) * 1000)

    content = (
        f"**Обход по запросу «{query}» завершён.**\n\n"
        f"- Найдено результатов: {len(results)}\n"
        f"- Успешно загружено: {fetched_count}\n"
        f"- Извлечено текста: {successful_count}\n"
        f"- Всего текста: {total_text_bytes} байт\n"
        f"- Время: {total_time_ms} мс\n"
    )

    return {
        "content": content,
        "artifacts": artifacts,
        "meta": {
            "total_results": len(results),
            "total_fetched": fetched_count,
            "total_extracted": successful_count,
            "total_text_bytes": total_text_bytes,
            "total_time_ms": total_time_ms,
            "query": query,
            "top_k": top_k,
        },
    }


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@mcp_bp.route("/tools/call", methods=["POST"])
def tools_call():
    """Call an MCP tool.

    Request JSON schema::

        {
            "tool": "search | crawl | fetch_page",
            "input": { … }
        }

    Supported tools:

    - **search** — Search SearXNG, no fetch.
        Input: ``{"query": str, "top_k": int (default 10)}``

    - **crawl** — Search → fetch all results → extract → save.
        Input: ``{"query": str, "top_k": int (default 5)}``

    - **fetch_page** — Fetch single URL → extract → save.
        Input: ``{"url": str}``
    """
    data = request.get_json(silent=True) or {}
    tool = data.get("tool", "")
    inp = data.get("input", {})

    try:
        if tool == "search":
            query = (inp.get("query") or "").strip()
            if not query:
                return jsonify({
                    "error": "Missing required field: input.query",
                    "valid_tools": ["search", "crawl", "fetch_page"],
                }), 400

            top_k = int(inp.get("top_k", 10))
            if top_k < 1:
                top_k = 1
            if top_k > 50:
                top_k = 50

            result = asyncio.run(_search_tool(query, top_k))
            return jsonify(result)

        elif tool == "crawl":
            query = (inp.get("query") or "").strip()
            if not query:
                return jsonify({
                    "error": "Missing required field: input.query",
                    "valid_tools": ["search", "crawl", "fetch_page"],
                }), 400

            top_k = int(inp.get("top_k", 5))
            if top_k < 1:
                top_k = 1
            if top_k > 20:
                top_k = 20

            result = asyncio.run(_crawl_tool(query, top_k))
            return jsonify(result)

        elif tool == "fetch_page":
            url = (inp.get("url") or "").strip()
            if not url:
                return jsonify({
                    "error": "Missing required field: input.url",
                    "valid_tools": ["search", "crawl", "fetch_page"],
                }), 400

            result = asyncio.run(_fetch_page_tool(url))
            return jsonify(result)

        else:
            return jsonify({
                "error": f"Unknown tool: {tool}",
                "valid_tools": ["search", "crawl", "fetch_page"],
            }), 400

    except Exception as exc:
        current_app.logger.exception("MCP tool '%s' failed", tool)
        return jsonify({
            "error": f"Internal error: {exc}",
            "tool": tool,
            "valid_tools": ["search", "crawl", "fetch_page"],
        }), 500