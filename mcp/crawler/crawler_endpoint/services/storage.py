"""Filesystem storage layer.

Saves raw HTML, extracted text, and maintains manifest.json.

Directory layout:
  /data/
    pages/
      2026.07.02/
        <sha256(url)>.<timestamp_ns>.html    # raw HTML
        <sha256(url)>.<timestamp_ns>.txt     # extracted text
    manifest.json           # JSON array of ManifestEntry
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import List

from crawler_endpoint.config import Settings
from crawler_endpoint.models import ManifestEntry


class StorageLayer:
    """Persists crawled content to the local filesystem.

    Saving is enabled only when the environment variable STORE_RESULTS is set
    to the literal string ``1`` (case-sensitive).  When disabled all public
    methods become no-ops and ``exists()`` always returns False.
    """

    def __init__(self, settings: Settings) -> None:
        self._data_path = Path(settings.data_path)
        self._pages_dir = self._data_path / "pages"
        self._manifest_path = self._data_path / "manifest.json"
        self._enabled: bool = os.environ.get("STORE_RESULTS") == "1"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_enabled(self) -> bool:
        """Return True if storage is enabled via STORE_RESULTS env var."""
        return self._enabled

    def save_html(self, url: str, html: str) -> str:
        """Save raw HTML and return the full path.

        Path: /data/pages/<YYYY.MM.DD>/<sha256(url)>.<timestamp_ns>.html

        Returns an empty string when storage is disabled.
        """
        if not self._enabled:
            return ""
        filepath = self._build_filepath(url, "html")
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(html, encoding="utf-8")
        return str(filepath)

    def save_text(self, url: str, text: str) -> str:
        """Save extracted text and return the full path.

        Path: /data/pages/<YYYY.MM.DD>/<sha256(url)>.<timestamp_ns>.txt

        Returns an empty string when storage is disabled.
        """
        if not self._enabled:
            return ""
        filepath = self._build_filepath(url, "txt")
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(text, encoding="utf-8")
        return str(filepath)

    def save_manifest(self, entry: ManifestEntry) -> None:
        """Append a ManifestEntry to manifest.json.

        No-op when storage is disabled.
        """
        if not self._enabled:
            return

        entries: List[dict] = []
        if self._manifest_path.exists():
            raw = self._manifest_path.read_text(encoding="utf-8").strip()
            if raw:
                try:
                    loaded = json.loads(raw)
                    if isinstance(loaded, list):
                        entries = loaded
                    else:
                        # If the file contains something else (dict, etc.),
                        # start fresh to avoid corruption.
                        entries = []
                except json.JSONDecodeError:
                    # Corrupted / empty JSON file – start fresh
                    entries = []

        entries.append(self._entry_as_dict(entry))

        self._manifest_path.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def exists(self, url: str) -> bool:
        """Check if a URL has already been fetched (by hash existence in any date dir)."""
        url_hash = self._url_hash(url)
        if not self._pages_dir.is_dir():
            return False
        for date_dir in self._pages_dir.iterdir():
            if not date_dir.is_dir():
                continue
            for f in date_dir.iterdir():
                # Match any file beginning with the hash (e.g. abc123.12345.txt)
                if f.name.startswith(url_hash) and f.suffix == ".txt":
                    return True
        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _url_hash(url: str) -> str:
        """Return hex-encoded SHA-256 digest of *url*."""
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    @staticmethod
    def _date_str() -> str:
        """Return current UTC date as YYYY.MM.DD."""
        return time.strftime("%Y.%m.%d", time.gmtime())

    @staticmethod
    def _timestamp_ns() -> int:
        """Return monotonic nanosecond timestamp for uniqueness."""
        return time.time_ns()

    def _build_filepath(self, url: str, ext: str) -> Path:
        """Build the full file path for a given URL and extension."""
        return (
            self._pages_dir
            / self._date_str()
            / f"{self._url_hash(url)}.{self._timestamp_ns()}.{ext}"
        )

    @staticmethod
    def _entry_as_dict(entry: ManifestEntry) -> dict:
        return {
            "url": entry.url,
            "hash": entry.hash,
            "title": entry.title,
            "fetched_at": entry.fetched_at,
            "fetch_time_ms": entry.fetch_time_ms,
            "extracted_with": entry.extracted_with,
            "text_bytes": entry.text_bytes,
        }