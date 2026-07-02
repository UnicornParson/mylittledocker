"""Filesystem storage layer.

Saves raw HTML, extracted text, and maintains manifest.json.
"""

from __future__ import annotations

from typing import List

from crawler_endpoint.config import Settings
from crawler_endpoint.models import CrawlResult, ManifestEntry


class StorageLayer:
    """Persists crawled content to the local filesystem."""

    def __init__(self, settings: Settings) -> None:
        self._data_path = settings.data_path

    def save_html(self, url: str, html: str) -> str:
        """Save raw HTML to /data/pages/<sha256(url)>.html and return the path."""
        # TODO: implement sha256-based idempotent HTML storage
        _ = url, html
        return ""

    def save_text(self, url: str, text: str) -> str:
        """Save extracted text to /data/pages/<sha256(url)>.txt and return the path."""
        # TODO: implement sha256-based idempotent text storage
        _ = url, text
        return ""

    def save_manifest(self, entry: ManifestEntry) -> None:
        """Append a ManifestEntry to manifest.json."""
        # TODO: implement append-only manifest persistence
        _ = entry

    def exists(self, url: str) -> bool:
        """Check if a URL has already been fetched (by hash existence)."""
        # TODO: implement idempotency check
        _ = url
        return False