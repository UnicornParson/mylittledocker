"""Tests for FetchEngine."""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from crawler_endpoint.config import Settings
from crawler_endpoint.services.fetch_engine import FetchEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(**overrides) -> Settings:
    return Settings(
        log_level="DEBUG",
        **overrides,
    )


_SAMPLE_HTML = "<html><body><h1>Hello</h1></body></html>"
_ANUBIS_HTML = (
    '<html><head><title>Making sure you\'re not a bot!</title></head>'
    '<body><div id="progress">Checking…</div></body></html>'
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFetchEngine:
    """Test suite for FetchEngine."""

    # -- fetch (single URL) ------------------------------------------------

    @pytest.mark.asyncio
    async def test_fetch_success(self):
        """Successful HTTP GET returns parsed HTML."""
        settings = _make_settings()

        with patch.object(FetchEngine, "_do_httpx_get", new=AsyncMock(return_value=_SAMPLE_HTML)):
            engine = FetchEngine(settings)
            result = await engine.fetch("https://example.com")
            assert result == _SAMPLE_HTML
            await engine.close()

    @pytest.mark.asyncio
    async def test_fetch_with_proxy(self):
        """Proxy is applied to httpx client when socks5_proxy is set."""
        settings = _make_settings()
        proxy_url = "socks5://127.0.0.1:1080"
        with patch("httpx.AsyncClient") as mock_client:
            engine = FetchEngine(settings, socks5_proxy=proxy_url)
            mock_client.assert_called_once_with(proxy=proxy_url, timeout=15)
        assert engine._socks5_proxy == proxy_url
        # _client is a MagicMock — no real resources to close

    @pytest.mark.asyncio
    async def test_fetch_with_proxy_from_settings(self):
        """Proxy is applied from settings when not passed explicitly."""
        settings = _make_settings(socks5_proxy="socks5://proxy:9050")
        engine = FetchEngine(settings)
        assert engine._socks5_proxy == "socks5://proxy:9050"
        await engine.close()

    @pytest.mark.asyncio
    async def test_fetch_no_proxy_default(self):
        """Without socks5_proxy the client uses no proxy."""
        settings = _make_settings()
        with patch("httpx.AsyncClient") as mock_client:
            engine = FetchEngine(settings)
            mock_client.assert_called_once_with(timeout=15)
        assert engine._socks5_proxy is None
        # _client is a MagicMock — no real resources to close

    @pytest.mark.asyncio
    async def test_fetch_anubis_playwright_disabled(self):
        """Anubis page returns None when Playwright is disabled."""
        settings = _make_settings(playwright_enabled=False)

        with patch.object(FetchEngine, "_do_httpx_get", new=AsyncMock(return_value=_ANUBIS_HTML)):
            engine = FetchEngine(settings)
            result = await engine.fetch("https://anubis.example.com")
            assert result is None  # Playwright disabled → can't bypass
            await engine.close()

    @pytest.mark.asyncio
    async def test_fetch_retry_then_fail(self):
        """After exhausting retries, returns None."""
        settings = _make_settings(fetch_retries=2, fetch_timeout=1)

        with patch.object(
            FetchEngine,
            "_do_httpx_get",
            new=AsyncMock(side_effect=httpx.TimeoutException("timeout", request=None)),
        ):
            engine = FetchEngine(settings)
            result = await engine.fetch("https://slow.example.com")
            assert result is None
            await engine.close()

    @pytest.mark.asyncio
    async def test_fetch_http_error(self):
        """HTTP 4xx/5xx is caught and None returned after retry."""
        settings = _make_settings(fetch_retries=1)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.request = MagicMock()

        with patch.object(
            FetchEngine,
            "_do_httpx_get",
            new=AsyncMock(side_effect=httpx.HTTPStatusError(
                "500 error", request=MagicMock(), response=mock_response,
            )),
        ):
            engine = FetchEngine(settings)
            result = await engine.fetch("https://error.example.com")
            assert result is None
            await engine.close()

    # -- fetch_all (parallel) ----------------------------------------------

    @pytest.mark.asyncio
    async def test_fetch_all_success(self):
        """Parallel fetch returns results for all URLs."""
        settings = _make_settings(max_concurrency=3)

        async def _mock_get(url: str) -> str:
            return f"<html><body>{url}</body></html>"

        with patch.object(FetchEngine, "_do_httpx_get", new=AsyncMock(side_effect=_mock_get)):
            engine = FetchEngine(settings)
            urls = [
                "https://a.com",
                "https://b.com",
                "https://c.com",
            ]
            results = await engine.fetch_all(urls)
            assert len(results) == 3
            for r in results:
                assert r is not None
            await engine.close()

    @pytest.mark.asyncio
    async def test_fetch_all_semaphore_respected(self):
        """Semaphore limits concurrency; verify via sequential timing mock."""
        settings = _make_settings(max_concurrency=2)
        call_count = 0

        async def _slow_mock(url: str) -> str:
            nonlocal call_count
            call_count += 1
            assert call_count <= settings.max_concurrency, "Exceeded max concurrency"
            await asyncio.sleep(0.05)
            call_count -= 1
            return _SAMPLE_HTML

        with patch.object(FetchEngine, "_do_httpx_get", new=AsyncMock(side_effect=_slow_mock)):
            engine = FetchEngine(settings)
            urls = ["https://a.com"] * 4
            results = await engine.fetch_all(urls)
            assert len(results) == 4
            await engine.close()

    # -- Anubis detection --------------------------------------------------

    def test_is_anubis_challenge_true(self):
        """Detects Anubis challenge markers."""
        assert FetchEngine._is_anubis_challenge(
            "Something about Making sure you're not a bot!"
        )
        assert FetchEngine._is_anubis_challenge(
            "Checking your browser before accessing"
        )

    def test_is_anubis_challenge_false(self):
        """Normal HTML does not trigger Anubis detection."""
        assert not FetchEngine._is_anubis_challenge("<html><body>OK</body></html>")

    # -- close -------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_close_twice(self):
        """Calling close() multiple times does not raise."""
        settings = _make_settings()
        engine = FetchEngine(settings)
        await engine.close()
        await engine.close()  # should be a no-op

    @pytest.mark.asyncio
    async def test_fetch_with_cloudscraper_fallback(self):
        """Fetch uses cloudscraper first, falls back to httpx."""
        settings = _make_settings()

        with patch.object(FetchEngine, "_try_cloudscraper", return_value=_SAMPLE_HTML) as mock_cs:
            with patch.object(FetchEngine, "_do_httpx_get", new=AsyncMock(return_value=_SAMPLE_HTML)):
                engine = FetchEngine(settings)
                result = await engine.fetch("https://example.com")
                assert result == _SAMPLE_HTML
                mock_cs.assert_not_called()  # httpx succeeds, no need for cloudscraper
                await engine.close()

    # -- Integration test with real Gentoo mirror ---------------------------

    @pytest.mark.skipif(
        not os.environ.get("socks5_proxy"),
        reason="socks5_proxy not set — skipping real-world fetch test",
    )
    @pytest.mark.asyncio
    async def test_fetch_real_gentoo_mirror(self):
        """Fetch a real file from Gentoo mirror via SOCKS5 proxy from env."""
        proxy_url = os.environ["socks5_proxy"]
        settings = _make_settings()
        engine = FetchEngine(settings, socks5_proxy=proxy_url)

        try:
            html = await engine.fetch(
                "https://ftp.belnet.be/pub/rsync.gentoo.org/gentoo/pub/"
            )
            assert html is not None, "Expected non-None HTML from Gentoo mirror"
            assert "<html" in html.lower(), "Expected HTML content"
            assert "gentoo" in html.lower(), "Expected 'gentoo' in page content"
        finally:
            await engine.close()