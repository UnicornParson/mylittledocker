"""FastMCP server with StreamableHTTP transport.

MCP API endpoint with tools:
- search      — Search SearXNG, no fetch
- crawl       — Search → fetch all results → extract all → save all
- fetch_page  — Fetch single URL → extract → save

Transport: StreamableHTTP (built-in FastAPI via FastMCP).
"""

from __future__ import annotations

import hashlib
import time
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator
from pathlib import Path
import json
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from mcp.server.transport_security import TransportSecuritySettings
from crawler_endpoint.di import Container
from crawler_endpoint.models import ManifestEntry, SearchResult


OUTPUT_LIMIT = 100 * 1024 # 100kb

# ---------------------------------------------------------------------------
# Global statistics counters (module-level, survive across tool calls)
# ---------------------------------------------------------------------------
import threading

_stats_lock = threading.Lock()
_stats_fetch_engine_bytes: int = 0  # bytes fetched via fetch_engine
_stats_total_bytes: int = 0         # total bytes fetched since startup


def reset_stats() -> None:
    """Reset statistics counters (useful for testing / manual reset)."""
    global _stats_fetch_engine_bytes, _stats_total_bytes
    with _stats_lock:
        _stats_fetch_engine_bytes = 0
        _stats_total_bytes = 0


def record_fetch_engine_bytes(size: int) -> None:
    """Record bytes fetched via fetch_engine."""
    global _stats_fetch_engine_bytes, _stats_total_bytes
    with _stats_lock:
        _stats_fetch_engine_bytes += size
        _stats_total_bytes += size


def format_bytes(size: int) -> str:
    """Format bytes into human-readable string (KB, MB, GB)."""
    if size < 0:
        return f"-{format_bytes(-size)}"
    if size == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    size_float = float(size)
    while size_float >= 1024.0 and idx < len(units) - 1:
        size_float /= 1024.0
        idx += 1
    # Show up to 2 decimal places, strip trailing zeros
    if size_float == int(size_float):
        return f"{int(size_float)} {units[idx]}"
    return f"{size_float:.2f} {units[idx]}"


def print_stats() -> None:
    """Print fetch_engine and total statistics to console."""
    with _stats_lock:
        fe_bytes = _stats_fetch_engine_bytes
        tot_bytes = _stats_total_bytes
    fe_str = format_bytes(fe_bytes)
    tot_str = format_bytes(tot_bytes)
    logger.info("📊 Статистика fetch_engine: %s | Всего загружено: %s", fe_str, tot_str)


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

logger = logging.getLogger("mcp.fastmcp")
logger.setLevel(logging.INFO)

if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    ))
    logger.addHandler(_handler)

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
# FastMCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "Crawler MCP Server",
    stateless_http=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
        allowed_hosts=["*"],
        allowed_origins=["*"],
    ),
)

# ---------------------------------------------------------------------------
# Tool handlers
# IMPORTANT: FastMCP generates correct MCP inputSchema only when tool
# functions accept scalar parameters (not Pydantic BaseModel).
# Using BaseModel args causes MCP clients to fail with "Field required" for 'args'.
# ---------------------------------------------------------------------------


@mcp.tool()
async def search(query: str, top_k: int = 10) -> str:
    """Search SearXNG and return results as a structured response."""
    # Clamp top_k
    if top_k < 1:
        top_k = 1
    if top_k > 50:
        top_k = 50

    logger.info("tool=search query=%s top_k=%d", query, top_k)
    start = time.monotonic()

    container = get_container()
    results: list[SearchResult] = await container.search_client.search(query, top_k)

    lines = [f"**Результаты поиска по запросу «{query}»:**"]
    for i, r in enumerate(results, 1):
        lines.append(f"\n{i}. [{r.title}]({r.url}) — {r.snippet}")

    content = "\n".join(lines) if results else f"По запросу «{query}» ничего не найдено."
    elapsed_ms = int((time.monotonic() - start) * 1000)

    logger.info(
        "tool=search query=%s top_k=%d results=%d elapsed_ms=%d",
        query, top_k, len(results), elapsed_ms,
    )

    return content


@mcp.prompt()
async def dummy_prompt() -> str:
    """Заглушка, чтобы клиент не ругался."""
    return ""


@mcp.tool()
async def fetch_page(url: str) -> str:
    """Fetch a single URL, extract content, save to disk, and return structured result."""
    logger.info("tool=fetch_page url=%s", url)
    start = time.monotonic()

    container = get_container()

    # 1. Fetch
    raw_html = await container.fetch_engine.fetch(url)
    if raw_html is None:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.warning("tool=fetch_page url=%s status=fetch_failed elapsed_ms=%d", url, elapsed_ms)
        return f"Не удалось загрузить страницу: {url}"

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
        text_bytes=len(text.encode("utf-8")),
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

    # Record fetch_engine stats (raw_html size)
    record_fetch_engine_bytes(len(raw_html.encode("utf-8")))

    # Build response
    snippet = text[:OUTPUT_LIMIT] + "…" if len(text) > OUTPUT_LIMIT else text
    content = f"**Страница:** {title or url}\n\n{snippet}"

    # Print statistics to console
    print_stats()

    return content

def truncate_at_sentence_end(text, max_chars=2000):
    text = text.replace('\n', " ").replace('  ', " ")
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    # Ищем последнюю точку, вопросительный или восклицательный знак
    last_punct = max(truncated.rfind('.'), truncated.rfind('?'), truncated.rfind('!'))
    if last_punct > 0:
        return truncated[:last_punct+1] + "..."
    else:
        return truncated + "..."  # если знаков препинания нет – режем как есть

@mcp.tool()
async def crawl(query: str, top_k: int = 5) -> str:
    """Full pipeline: search → fetch all → extract all → save all → return text content."""
    # Clamp top_k
    if top_k < 1:
        top_k = 1
    if top_k > 20:
        top_k = 20

    logger.info("tool=crawl query=%s top_k=%d", query, top_k)
    total_start = time.monotonic()

    container = get_container()

    # 1. Search
    results: list[SearchResult] = await container.search_client.search(query, top_k)
    if not results:
        elapsed_ms = int((time.monotonic() - total_start) * 1000)
        logger.warning("tool=crawl query=%s top_k=%d status=no_results elapsed_ms=%d", query, top_k, elapsed_ms)
        return f"По запросу «{query}» ничего не найдено."

    urls = [r.url for r in results]

    # 2. Fetch all in parallel
    html_bodies = await container.fetch_engine.fetch_all(urls)

    # 3. Extract, save & collect text content
    fetched_count = 0
    pages: list[dict[str, str]] = []

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

        pages.append({"url": url, "title": title, "text": truncate_at_sentence_end(text, 4096)})

    # 4. If no page could be fetched, return LLM-friendly error
    if fetched_count == 0:
        total_time_ms = int((time.monotonic() - total_start) * 1000)
        logger.warning(
            "tool=crawl query=%s top_k=%d status=all_fetch_failed elapsed_ms=%d",
            query, top_k, total_time_ms,
        )
        return (
            "CRAWLER_UNAVAILABLE: Crawler is currently unable to fetch any pages. "
            "The website(s) may be unreachable, blocking requests, or the fetch engine "
            "is experiencing connectivity issues. Try again later or use a different query."
        )

    # 5. Build text content response
    parts: list[str] = []
    for page in pages:
        header = f"## {page['title']}\nSource: {page['url']}"
        content_body = page["text"] if page["text"] else "(No extractable text content)"
        parts.append(f"{header}\n\n{content_body}")

    result_text = "\n\n---\n\n".join(parts)

    total_time_ms = int((time.monotonic() - total_start) * 1000)
    logger.info(
        "tool=crawl query=%s top_k=%d results=%d fetched=%d elapsed_ms=%d",
        query, top_k, len(results), fetched_count, total_time_ms,
    )

    # Record fetch_engine stats for each fetched page (use raw HTML size)
    for url, result in zip(urls, html_bodies):
        if result is not None:
            record_fetch_engine_bytes(len(result.encode("utf-8")))

    # Print statistics to console
    print_stats()

    return json.dumps(pages, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Starlette application from FastMCP
# ---------------------------------------------------------------------------

appf = mcp.streamable_http_app()
appf.user_middleware = []
appf.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
