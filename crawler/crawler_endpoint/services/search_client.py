"""SearXNG HTTP client.

Provides async search via SearXNG with result normalization.
"""

from __future__ import annotations

from typing import List

import httpx

from crawler_endpoint.config import Settings
from crawler_endpoint.models import SearchResult


class SearchClient:
    """Async HTTP client for SearXNG search engine."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.searxng_url
        self._client = httpx.AsyncClient(timeout=10.0)

    async def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """Execute search query via SearXNG and return normalized results."""
        # TODO: implement actual SearXNG API call
        _ = query, top_k
        return []

    async def close(self) -> None:
        """Close underlying HTTP client."""
        await self._client.aclose()