"""Tests for the SearchClient service."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from crawler_endpoint.config import Settings
from crawler_endpoint.models import SearchResult
from crawler_endpoint.services.search_client import SearchClient


@pytest.fixture
def settings() -> Settings:
    """Return a test Settings instance pointed at a fake base url."""
    return Settings(searxng_url="http://fake-searxng:8080")


@pytest.fixture
def client(settings: Settings) -> SearchClient:
    """Return a SearchClient instance with the fake settings."""
    return SearchClient(settings)


@pytest.mark.asyncio
async def test_search_returns_results(client: SearchClient):
    """SearchClient should return a list of SearchResult objects."""
    mock_response = {
        "results": [
            {
                "url": "https://example.com",
                "title": "Example Title",
                "content": "Example snippet.",
                "engine": "google",
                "score": 0.95,
            },
            {
                "url": "https://example.org",
                "title": "Org Title",
                "content": "Org snippet.",
                "engine": "bing",
                "score": 0.80,
            },
        ]
    }

    with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(200, json=mock_response)

        results = await client.search("test query")

    assert len(results) == 2

    assert isinstance(results[0], SearchResult)
    assert results[0].url == "https://example.com"
    assert results[0].title == "Example Title"
    assert results[0].snippet == "Example snippet."
    assert results[0].engine == "google"
    assert results[0].score == 0.95

    assert results[1].url == "https://example.org"
    assert results[1].title == "Org Title"
    assert results[1].snippet == "Org snippet."
    assert results[1].engine == "bing"
    assert results[1].score == 0.80


@pytest.mark.asyncio
async def test_search_empty_query(client: SearchClient):
    """SearchClient should handle empty query gracefully."""
    results = await client.search("   ")
    assert results == []


@pytest.mark.asyncio
async def test_search_http_error(client: SearchClient):
    """SearchClient should return empty list on HTTP error."""
    with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPStatusError(
            "500 error", request=httpx.Request("GET", "http://fake"),
            response=httpx.Response(500),
        )
        results = await client.search("query")
    assert results == []


@pytest.mark.asyncio
async def test_search_connection_error(client: SearchClient):
    """SearchClient should return empty list on connection error."""
    with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.RequestError("connection failed")
        results = await client.search("query")
    assert results == []


@pytest.mark.asyncio
async def test_search_no_results_key(client: SearchClient):
    """SearchClient should return empty list when JSON has no 'results' key."""
    with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(200, json={"some": "data"})
        results = await client.search("query")
    assert results == []


@pytest.mark.asyncio
async def test_search_invalid_json(client: SearchClient):
    """SearchClient should return empty list on invalid JSON."""
    with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = ValueError("bad json")
        results = await client.search("query")
    assert results == []


@pytest.mark.asyncio
async def test_search_top_k(client: SearchClient):
    """SearchClient should respect the top_k parameter."""
    mock_response = {
        "results": [
            {
                "url": f"https://example.com/{i}",
                "title": f"Title {i}",
                "content": f"Snippet {i}",
                "engine": "google",
                "score": 1.0 - i * 0.1,
            }
            for i in range(20)
        ]
    }

    with patch.object(client._client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(200, json=mock_response)
        results = await client.search("query", top_k=5)

    assert len(results) == 5


@pytest.mark.asyncio
async def test_close(client: SearchClient):
    """SearchClient.close() should close the HTTP client without error."""
    with patch.object(client._client, "aclose", new_callable=AsyncMock) as mock_close:
        await client.close()
    mock_close.assert_awaited_once()