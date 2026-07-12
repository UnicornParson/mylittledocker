"""Dataclasses / pydantic models for the crawler pipeline.

Defines SearchResult, CrawlResult, and ManifestEntry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SearchResult:
    """Normalized search result from SearXNG."""

    url: str
    title: str
    snippet: str
    engine: str
    score: float


@dataclass
class CrawlResult:
    """Result of fetching and extracting a single page."""

    url: str
    title: Optional[str] = None
    text: str = ""
    html_path: str = ""
    text_path: str = ""
    fetch_time_ms: int = 0
    extracted_with: str = ""


@dataclass
class ManifestEntry:
    """Persistent manifest entry written to manifest.json."""

    url: str
    hash: str
    title: str
    fetched_at: str
    fetch_time_ms: int
    extracted_with: str
    text_bytes: int