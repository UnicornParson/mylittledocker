"""Extractor: trafilatura + readability fallback.

Extracts title and text content from raw HTML.
"""

from __future__ import annotations

from typing import Optional

from readability import Document
from trafilatura import extract as tf_extract


class ExtractResult:
    """Result of content extraction from HTML."""

    def __init__(self, title: Optional[str] = None, text: str = "") -> None:
        self.title = title
        self.text = text


class Extractor:
    """Content extractor with trafilatura primary and readability fallback."""

    def extract(self, html: str) -> ExtractResult:
        """Extract title and text from raw HTML.

        Uses trafilatura first (best quality extraction).
        Falls back to readability-lxml for pages where trafilatura returns
        no meaningful content.

        Args:
            html: Raw HTML string to extract content from.

        Returns:
            ExtractResult with extracted title and text.
            Both fields may be empty if no content could be extracted.
        """
        if not html or not html.strip():
            return ExtractResult(title=None, text="")

        # Primary extraction with trafilatura
        import json

        raw = tf_extract(html, output_format="json", include_comments=False, include_tables=False)

        if raw:
            try:
                result = json.loads(raw)
            except json.JSONDecodeError:
                result = None
        else:
            result = None

        if result is not None and result.get("text"):
            title = result.get("title") or None
            # Fallback: extract <title> from raw HTML if trafilatura didn't find it
            if not title:
                import re as _re
                m = _re.search(r"<title[^>]*>(.*?)</title>", html, _re.IGNORECASE | _re.DOTALL)
                if m:
                    title = m.group(1).strip() or None
            return ExtractResult(title=title, text=result["text"])

        # Fallback to readability-lxml
        try:
            doc = Document(html)
            title = doc.title() or None
            text = doc.summary()

            if not text:
                return ExtractResult(title=None, text="")

            # Strip HTML tags from readability output to get plain text
            import re
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()

            return ExtractResult(title=title, text=text)
        except Exception:
            # If readability also fails, return empty result
            return ExtractResult(title=None, text="")