"""Async fetch engine with SOCKS5 proxy support, retry, Anubis bypass via Playwright.

Based on ContentLoader example from crawler/notes/ContentLoader.md.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import List, Optional

import cloudscraper
import httpx
import html

from crawler_endpoint.config import Settings

logger = logging.getLogger("crawler_endpoint.FetchEngine")


class FetchEngine:
    """Async fetcher for web pages with retry, Anubis bypass, and optional SOCKS5 proxy.

    If ``socks5_proxy`` is provided (e.g. ``socks5://127.0.0.1:9050``) then
    **all** HTTP fetches are forced through that proxy.  Playwright-based
    Anubis bypass also respects the proxy.
    """

    def __init__(
        self,
        settings: Settings,
        socks5_proxy: str | None = None,
    ) -> None:
        # If socks5_proxy is not explicitly passed, fall back to settings value
        self._socks5_proxy = socks5_proxy or settings.socks5_proxy

        self._max_concurrency = settings.max_concurrency
        self._timeout = settings.fetch_timeout
        self._retries = settings.fetch_retries
        self._playwright_enabled = settings.playwright_enabled

        # Build the async HTTP client; apply SOCKS5 proxy if configured
        client_kwargs: dict = {"timeout": self._timeout}
        if self._socks5_proxy:
            client_kwargs["proxy"] = self._socks5_proxy
        self._client = httpx.AsyncClient(**client_kwargs)

        self._semaphore = asyncio.Semaphore(self._max_concurrency)
        self._playwright: "async_playwright.Playwright | None" = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch(self, url: str) -> Optional[str]:
        """Fetch a single URL and return raw HTML, or ``None`` on failure.

        The flow is:

        1. Try ``cloudscraper`` (synchronous, respects proxy if configured).
        2. If the response body looks like an Anubis challenge, use Playwright
           to bypass it.
        3. If Playwright is disabled or unavailable, return the raw body
           (which may be the challenge page).
        """
        raw = await self._try_fetch_with_retry(url)
        if raw is None:
            return None

        if self._is_anubis_challenge(raw):
            logger.info("Anubis challenge detected for %s, attempting bypass …", url)
            return await self._fetch_with_anubis_bypass(url)

        return raw

    async def fetch_all(self, urls: List[str]) -> List[Optional[str]]:
        """Fetch multiple URLs in parallel, limited by ``max_concurrency``.

        Preserves the order of results matching the input URLs.
        If a single URL fails (exception or None) it's returned as None
        in the corresponding position.
        """
        sem = self._semaphore

        async def _fetch_one(url: str) -> tuple[int, Optional[str]]:
            """Return (index, html_or_None) so we can restore order."""
            async with sem:
                try:
                    html = await self.fetch(url)
                    return (urls.index(url), html)
                except Exception as exc:
                    logger.error("Unhandled error in fetch_all for %s: %s", url, exc)
                    return (urls.index(url), None)

        tasks = [asyncio.create_task(_fetch_one(u)) for u in urls]
        ordered: list[Optional[str]] = [None] * len(urls)
        for coro in asyncio.as_completed(tasks):
            idx, html = await coro
            ordered[idx] = html
        return ordered

    async def close(self) -> None:
        """Close underlying HTTP client and Playwright resources."""
        await self._client.aclose()
        if self._playwright is not None:
            await self._playwright.stop()

    # ------------------------------------------------------------------
    # Internal: HTTP fetch with retry
    # ------------------------------------------------------------------

    async def _try_fetch_with_retry(self, url: str) -> Optional[str]:
        """Try HTTP GET via :class:`httpx.AsyncClient` with retries.

        The first attempt is actually done with ``cloudscraper`` (which has
        its own retry logic for JS challenges), and if that fails we fall
        back to plain ``httpx``.
        """
        last_exc: Optional[Exception] = None

        for attempt in range(1, self._retries + 2):  # 1 initial + retries
            try:
                return await self._do_httpx_get(url)
            except httpx.TimeoutException as exc:
                logger.warning(
                    "Timeout fetching %s (attempt %d/%d)", url, attempt, self._retries + 1
                )
                last_exc = exc
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "HTTP %d fetching %s (attempt %d/%d)",
                    exc.response.status_code,
                    url,
                    attempt,
                    self._retries + 1,
                )
                last_exc = exc
            except Exception as exc:
                logger.error("Unexpected error fetching %s: %s", url, exc)
                last_exc = exc
                break  # non-retryable

            # Exponential backoff before next attempt
            if attempt <= self._retries:
                await asyncio.sleep(0.5 * (2 ** (attempt - 1)))

        logger.error("All attempts failed for %s: %s", url, last_exc)
        return None

    async def _do_httpx_get(self, url: str) -> str:
        """Perform a single HTTP GET via ``httpx``.

        If a SOCKS5 proxy is configured, the request is automatically
        routed through it because the client was built with ``proxies=…``.
        """
        resp = await self._client.get(url, follow_redirects=True)
        resp.raise_for_status()
        return resp.text

    # ------------------------------------------------------------------
    # Internal: cloudscraper (synchronous, proxy-aware)
    # ------------------------------------------------------------------

    def _try_cloudscraper(self, url: str) -> Optional[str]:
        """Use ``cloudscraper`` as a first-line defence against simple JS challenges.

        If a SOCKS5 proxy is configured, we pass it via the ``proxies``
        argument so that the request is tunnelled through the proxy.
        """
        try:
            scraper = cloudscraper.create_scraper()
            proxies: dict | None = None
            if self._socks5_proxy:
                proxies = {
                    "http": self._socks5_proxy,
                    "https": self._socks5_proxy,
                }
            resp = scraper.get(url, timeout=self._timeout, proxies=proxies)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            logger.debug("cloudscraper failed for %s: %s", url, exc)
            return None

    # ------------------------------------------------------------------
    # Internal: Anubis detection and bypass
    # ------------------------------------------------------------------

    @staticmethod
    def _is_anubis_challenge(body: str) -> bool:
        """Heuristic check for Anubis challenge page."""
        markers = [
            "Making sure you're not a bot",
            "anubis",
            "challenge-platform",
            "Checking your browser",
        ]
        lower = body.lower()
        return any(m.lower() in lower for m in markers)

    async def _fetch_with_anubis_bypass(self, url: str, timeout: int = 60) -> Optional[str]:
        """Open URL in headless Chromium via Playwright and wait for Anubis
        verification to complete.

        If a SOCKS5 proxy is configured, we pass it as a browser launch
        argument so Playwright routes traffic through the same proxy.
        """
        if not self._playwright_enabled:
            logger.warning(
                "Anubis detected but Playwright is disabled (%s)", url
            )
            # Return whatever we got – it's the challenge page, but callers
            # may still want to save it.
            return None

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("playwright is not installed – cannot bypass Anubis for %s", url)
            return None

        p = await async_playwright().start()
        self._playwright = p  # keep reference for cleanup

        launch_args: dict = {"headless": True}
        if self._socks5_proxy:
            # Playwright's proxy config expects a dict with "server"
            launch_args["proxy"] = {"server": self._socks5_proxy}

        browser = await p.chromium.launch(**launch_args)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
        )

        page = await context.new_page()
        logger.info("Playwright navigating to %s", url)

        try:
            await page.goto(url, wait_until="domcontentloaded")

            # --- Anubis detection & bypass loop ---
            initial_content = await page.content()
            initial_content = html.unescape(initial_content)

            if not self._is_anubis_challenge(initial_content):
                # Not actually an Anubis page – return as-is
                logger.info("No Anubis challenge on %s", url)
                return initial_content

            logger.info("Waiting for Anubis verification on %s …", url)
            await page.wait_for_selector(
                "text=Making sure you're not a bot!",
                timeout=timeout * 1000,
            )

            # Wait for the progress bar to finish
            try:
                progress_bar = page.locator("#progress")
                logger.info("Waiting for progress bar completion …")
                start_time = time.time()
                while time.time() - start_time < timeout:
                    class_list = await progress_bar.get_attribute("class") or ""
                    if "hidden" in class_list or "invisible" in class_list:
                        logger.info("Progress bar hidden – verification likely done.")
                        break
                    await asyncio.sleep(0.5)
                else:
                    logger.warning("Progress bar timeout on %s", url)
            except Exception:
                logger.info("Progress bar not found on %s, using fallback wait", url)
                await page.wait_for_timeout(15000)

            await page.wait_for_load_state("networkidle")

            # Double-check that the challenge is gone
            still_present = await page.query_selector(
                "text=Making sure you're not a bot!"
            )
            if still_present:
                logger.error("Anubis verification still present on %s", url)
                await page.screenshot(path="anubis_error.png")
                return None

            logger.info("Anubis bypass successful for %s", url)
            content = await page.content()
            return html.unescape(content)

        except Exception as exc:
            logger.error("Playwright error for %s: %s", url, exc)
            await page.screenshot(path="anubis_error.png")
            return None
        finally:
            await browser.close()