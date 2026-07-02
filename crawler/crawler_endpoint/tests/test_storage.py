"""Tests for StorageLayer."""

import json

import pytest
from pathlib import Path
from crawler_endpoint.config import Settings
from crawler_endpoint.models import ManifestEntry
from crawler_endpoint.services.storage import StorageLayer


class TestStorageLayer:
    """Test suite for StorageLayer."""

    @pytest.fixture
    def storage(self, tmp_path) -> StorageLayer:
        """Create a StorageLayer backed by a temporary directory."""
        settings = Settings(data_path=str(tmp_path))
        return StorageLayer(settings)

    def test_save_html_creates_file(self, storage: StorageLayer) -> None:
        """save_html writes content to the correct path."""
        url = "https://example.com/page"
        html = "<html><body><h1>Hello</h1></body></html>"

        path = storage.save_html(url, html)

        # Path must exist and contain the expected content
        assert Path(path).exists()
        assert Path(path).read_text(encoding="utf-8") == html

    def test_save_text_creates_file(self, storage: StorageLayer) -> None:
        """save_text writes content to the correct path."""
        url = "https://example.com/page"
        text = "Hello world"

        path = storage.save_text(url, text)

        assert Path(path).exists()
        assert Path(path).read_text(encoding="utf-8") == text

    def test_filepath_contains_date_dir(self, storage: StorageLayer) -> None:
        """The returned path contains a date directory like 2026.07.02."""
        url = "https://example.com/page"
        path = storage.save_html(url, "<html/>")

        path_obj = Path(path)
        # parent dir name should match YYYY.MM.DD pattern
        date_dir = path_obj.parent.name
        assert len(date_dir) == 10  # e.g. "2026.07.02"

    def test_same_url_same_hash_stem(self, storage: StorageLayer) -> None:
        """save_html + save_text for the same URL share the same hash prefix."""
        url = "https://example.com/page"
        html_path = storage.save_html(url, "<html/>")
        text_path = storage.save_text(url, "text")

        html_stem = Path(html_path).stem  # hash.timestamp
        text_stem = Path(text_path).stem

        # Both should start with the same sha256 hash before the dot
        html_hash = html_stem.split(".")[0]
        text_hash = text_stem.split(".")[0]
        assert html_hash == text_hash

    def test_save_manifest_appends(self, storage: StorageLayer) -> None:
        """save_manifest appends entries and persists them."""
        entry = ManifestEntry(
            url="https://example.com",
            hash="abc123",
            title="Example",
            fetched_at="2026-07-02T17:00:00Z",
            fetch_time_ms=150,
            extracted_with="trafilatura",
            text_bytes=42,
        )

        storage.save_manifest(entry)

        manifest_path = storage._manifest_path  # type: ignore[attr-defined]
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["url"] == "https://example.com"

        # Append a second entry
        entry2 = ManifestEntry(
            url="https://other.com",
            hash="def456",
            title="Other",
            fetched_at="2026-07-02T18:00:00Z",
            fetch_time_ms=200,
            extracted_with="readability",
            text_bytes=99,
        )
        storage.save_manifest(entry2)

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert len(data) == 2

    def test_exists_returns_false_for_unknown(self, storage: StorageLayer) -> None:
        """exists returns False when no .txt file exists for the URL."""
        assert not storage.exists("https://example.com/unknown")

    def test_exists_returns_true_after_save(self, storage: StorageLayer) -> None:
        """exists returns True after save_text has been called."""
        url = "https://example.com/page"
        storage.save_text(url, "content")
        assert storage.exists(url)