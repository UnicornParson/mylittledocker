"""Extractor: trafilatura + readability fallback.

Extracts title and text content from raw HTML.
"""

from __future__ import annotations

from typing import Optional


class ExtractResult:
    """Result of content extraction from HTML."""

    def __init__(self, title: Optional[str] = None, text: str = "") -> None:
        self.title = title
        self.text = text


class Extractor:
    """Content extractor with trafilatura primary and readability fallback."""

    def extract(self, html: str) -> ExtractResult:
        """Extract title and text from raw HTML."""
        # TODO: implement trafilatura.extract() with readability fallback
        _ = html
        return ExtractResult(title=None, text="")