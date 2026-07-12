"""SearXNG HTTP client.

Provides async search via SearXNG with result normalization.
SearXNG is available at http://searxng:8080 (same docker network).
"""

from __future__ import annotations

from typing import List

import httpx

from crawler_endpoint.config import Settings
from crawler_endpoint.models import SearchResult


class SearchClient:
    """Async HTTP client for SearXNG search engine."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.searxng_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=10.0)

    async def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """Execute search query via SearXNG and return normalized results.

        Calls SearXNG JSON API at ``GET /search?format=json&q=<query>``.

        Parameters
        ----------
        query : str
            Search query string.
        top_k : int
            Maximum number of results to return (default 10).

        Returns
        -------
        List[SearchResult]
            Normalized search results. Empty list on error or missing results.
        """
        stripped = query.strip()
        if not stripped:
            return []

        url = f"{self._base_url}/search"
        params = {"q": stripped, "format": "json"}

        try:
            response = await self._client.get(url, params=params)
            if response.status_code >= 400:
                return []
            data = response.json()
        except (httpx.HTTPError, ValueError):
            # On any HTTP/connection/parse error return empty list.
            # In production a proper logger call can be added here.
            return []

        raw_results: list[dict] = data.get("results", [])
        if not raw_results:
            return []

        results: List[SearchResult] = []
        for item in raw_results[:top_k]:
            results.append(
                SearchResult(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    snippet=item.get("content", ""),
                    engine=item.get("engine", ""),
                    score=float(item.get("score", 0.0)),
                )
            )

        return results

    async def close(self) -> None:
        """Close underlying HTTP client."""
        await self._client.aclose()