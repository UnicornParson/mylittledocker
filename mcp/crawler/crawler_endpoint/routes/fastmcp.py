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

from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from mcp.server.transport_security import TransportSecuritySettings
from crawler_endpoint.di import Container
from crawler_endpoint.models import ManifestEntry, SearchResult

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
# Pydantic models for tool arguments
# ---------------------------------------------------------------------------


class SearchArgs(BaseModel):
    """Arguments for the search tool."""
    query: str = Field(..., description="The search query string")
    top_k: int = Field(10, ge=1, le=50, description="Number of results to return (1-50, default 10)")


class FetchPageArgs(BaseModel):
    """Arguments for the fetch_page tool."""
    url: str = Field(..., description="The URL to fetch and extract")


class CrawlArgs(BaseModel):
    """Arguments for the crawl tool."""
    query: str = Field(..., description="The search query string")
    top_k: int = Field(5, ge=1, le=20, description="Number of results to process (1-20, default 5)")

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
# ---------------------------------------------------------------------------


@mcp.tool()
async def search(args: SearchArgs) -> str:
    """Search SearXNG and return results as a structured response."""
    query = args.query
    top_k = args.top_k

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
async def fetch_page(args: FetchPageArgs) -> str:
    """Fetch a single URL, extract content, save to disk, and return structured result."""
    url = args.url

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
    content = f"**Страница:** {title or url}\n\n{snippet}"

    return content


@mcp.tool()
async def crawl(args: CrawlArgs) -> str:
    """Full pipeline: search → fetch all → extract all → save all."""
    query = args.query
    top_k = args.top_k

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
    return content


# ---------------------------------------------------------------------------
# Starlette application from FastMCP
# ---------------------------------------------------------------------------

appf = mcp.streamable_http_app()
appf.user_middleware = []
appf.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

print("222")