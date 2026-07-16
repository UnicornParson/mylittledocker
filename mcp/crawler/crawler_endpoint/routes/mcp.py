"""FastMCP server with SSE transport.

MCP API endpoint with tools:
- search      — Search SearXNG, no fetch
- crawl       — Search → fetch all results → extract → save
- fetch_page  — Fetch single URL → extract → save

The DI container is accessed via the module-level ``get_container()``
helper which lazily creates a singleton ``Container``.

Transport: SSE (Streaming HTTP) on a dedicated port.
"""

from __future__ import annotations

import hashlib
import time
import logging
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import (
    Tool,
    TextContent,
    ListToolsResult,
    CallToolResult,
    Prompt,
    ListPromptsResult,
)
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse

from crawler_endpoint.di import Container
from crawler_endpoint.models import ManifestEntry, SearchResult

# ---------------------------------------------------------------------------
# Console logger for MCP tool calls
# ---------------------------------------------------------------------------

logger = logging.getLogger("mcp.tools")
logger.setLevel(logging.INFO)

# Ensure there's always a stderr handler so logs appear in container logs
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    ))
    logger.addHandler(_handler)

# ---------------------------------------------------------------------------
# MCP Server instance (Anthropic SDK)
# ---------------------------------------------------------------------------

mcp_server = Server("Crawler MCP Server")

# ---------------------------------------------------------------------------
# DI singleton helper
# ---------------------------------------------------------------------------

_container: Container | None = None


def get_container() -> Container:
    """Return the singleton DI container (lazily created on first call)."""
    global _container
    if _container is None:
        _container = Container()
    return _container


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

@mcp_server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="search",
            description="Search SearXNG and return results as a structured response",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (1-50, default 10)",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="fetch_page",
            description="Fetch a single URL, extract content, save to disk, and return structured result",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch and extract",
                    },
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="crawl",
            description="Full pipeline: search → fetch all → extract all → save all",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to process (1-20, default 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
    ]


@mcp_server.list_prompts()
async def handle_list_prompts() -> ListPromptsResult:
    """Return empty list of prompts — this server only provides tools."""
    return ListPromptsResult(prompts=[])


@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "search":
        return await _call_search(arguments)
    elif name == "fetch_page":
        return await _call_fetch_page(arguments)
    elif name == "crawl":
        return await _call_crawl(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


async def _call_search(arguments: dict) -> list[TextContent]:
    query = arguments["query"]
    top_k = arguments.get("top_k", 10)
    if top_k < 1:
        top_k = 1
    if top_k > 50:
        top_k = 50

    logger.info("tool=search query=%s top_k=%d", query, top_k)
    start = time.monotonic()

    container = get_container()
    results: List[SearchResult] = await container.search_client.search(query, top_k)

    lines = [f"**Результаты поиска по запросу «{query}»:**"]
    for i, r in enumerate(results, 1):
        lines.append(f"\n{i}. [{r.title}]({r.url}) — {r.snippet}")

    content = "\n".join(lines) if results else f"По запросу «{query}» ничего не найдено."
    elapsed_ms = int((time.monotonic() - start) * 1000)

    logger.info(
        "tool=search query=%s top_k=%d results=%d elapsed_ms=%d",
        query, top_k, len(results), elapsed_ms,
    )

    return [TextContent(type="text", text=content)]


async def _call_fetch_page(arguments: dict) -> list[TextContent]:
    url = arguments["url"]
    logger.info("tool=fetch_page url=%s", url)
    start = time.monotonic()

    container = get_container()

    # 1. Fetch
    raw_html = await container.fetch_engine.fetch(url)
    if raw_html is None:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.warning("tool=fetch_page url=%s status=fetch_failed elapsed_ms=%d", url, elapsed_ms)
        return [TextContent(type="text", text=f"Не удалось загрузить страницу: {url}")]

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

    elapsed_ms = int((time.monotonic() - start) * 1000)
    logger.info(
        "tool=fetch_page url=%s title=%s text_bytes=%d fetch_time_ms=%d elapsed_ms=%d",
        url, title, text_bytes, fetch_time_ms, elapsed_ms,
    )

    # Build response
    snippet = text[:500] + "…" if len(text) > 500 else text
    content = (
        f"**Страница:** {title or url}\n\n"
        f"{snippet}"
    )

    return [TextContent(type="text", text=content)]


async def _call_crawl(arguments: dict) -> list[TextContent]:
    query = arguments["query"]
    top_k = arguments.get("top_k", 5)
    if top_k < 1:
        top_k = 1
    if top_k > 20:
        top_k = 20

    logger.info("tool=crawl query=%s top_k=%d", query, top_k)
    total_start = time.monotonic()

    container = get_container()

    # 1. Search
    results: List[SearchResult] = await container.search_client.search(query, top_k)
    if not results:
        elapsed_ms = int((time.monotonic() - total_start) * 1000)
        logger.warning("tool=crawl query=%s top_k=%d status=no_results elapsed_ms=%d", query, top_k, elapsed_ms)
        return [TextContent(type="text", text=f"По запросу «{query}» ничего не найдено.")]

    urls = [r.url for r in results]

    # 2. Fetch all in parallel
    html_bodies = await container.fetch_engine.fetch_all(urls)

    # 3. Extract & save
    fetched_count = 0
    successful_count = 0
    total_text_bytes = 0

    for url, result in zip(urls, html_bodies):
        if result is None:
            logger.warning("tool=crawl query=%s url=%s status=fetch_failed", query, url)
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
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
        manifest_entry = ManifestEntry(
            url=url,
            hash=url_hash,
            title=title,
            fetched_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            fetch_time_ms=0,
            extracted_with="trafilatura/readability",
            text_bytes=text_bytes,
        )
        container.storage.save_manifest(manifest_entry)

    total_time_ms = int((time.monotonic() - total_start) * 1000)
    content = (
        f"**Результат crawl по запросу «{query}»:**\n\n"
        f"Найдено ссылок: {len(results)}\n"
        f"Успешно загружено: {fetched_count}\n"
        f"Извлечено контента: {successful_count}\n"
        f"Объём текста: {total_text_bytes} байт\n"
        f"Время выполнения: {total_time_ms} мс"
    )
    logger.info(
        "tool=crawl query=%s top_k=%d results=%d fetched=%d extracted=%d text_bytes=%d elapsed_ms=%d",
        query, top_k, len(results), fetched_count, successful_count, total_text_bytes, total_time_ms,
    )
    return [TextContent(type="text", text=content)]


# ---------------------------------------------------------------------------
# SSE Transport & ASGI application
# ---------------------------------------------------------------------------

sse_transport = SseServerTransport("/mcp/")


async def _handle_post_message(scope, receive, send):
    """Wrapper to handle POST messages (delegates to SseServerTransport)."""
    await sse_transport.handle_post_message(scope, receive, send)


async def sse_app(scope, receive, send):
    """ASGI application: GET → establish SSE stream, POST → message handling."""
    if scope["method"] == "GET":
        async with sse_transport.connect_sse(scope, receive, send) as streams:
            read_stream, write_stream = streams
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )
    else:
        await _handle_post_message(scope, receive, send)


mcp_app = Starlette(
    routes=[
        Mount("/mcp", app=sse_app),
    ]
)
