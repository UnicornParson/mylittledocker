"""Async fetch (httpx) + optional Playwright fallback."""

from __future__ import annotations

from typing import List, Optional

import httpx

from crawler_endpoint.config import Settings


class FetchEngine:
    """Async fetcher for web pages with retry and optional Playwright fallback."""

    def __init__(self, settings: Settings) -> None:
        self._max_concurrency = settings.max_concurrency
        self._timeout = settings.fetch_timeout
        self._retries = settings.fetch_retries
        self._playwright_enabled = settings.playwright_enabled
        self._client = httpx.AsyncClient(timeout=self._timeout)

    async def fetch(self, url: str) -> Optional[str]:
        """Fetch a single URL and return raw HTML, or None on failure."""
        # TODO: implement fetch with retry and optional Playwright fallback
        _ = url
        return None

    async def fetch_all(self, urls: List[str]) -> List[Optional[str]]:
        """Fetch multiple URLs in parallel (semaphore-limited)."""
        # TODO: implement parallel fetch with semaphore
        _ = urls
        return []

    async def close(self) -> None:
        """Close underlying HTTP client."""
        await self._client.aclose()