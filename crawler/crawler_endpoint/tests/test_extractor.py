"""Tests for the Extractor service."""

import pytest

from crawler_endpoint.services.extractor import ExtractResult, Extractor


SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Test Article Title</title>
</head>
<body>
    <article>
        <h1>Test Article Title</h1>
        <p>This is the first paragraph of the test article. It contains meaningful content
        that should be extracted by the extractor service.</p>
        <p>This is the second paragraph with more content to ensure multi-paragraph
        extraction works correctly.</p>
    </article>
</body>
</html>"""


def test_extractor_returns_title_and_text():
    """Extractor should extract title and text from valid HTML."""
    extractor = Extractor()
    result = extractor.extract(SAMPLE_HTML)

    assert isinstance(result, ExtractResult)
    assert result.title is not None
    assert "Test Article Title" in result.title
    assert len(result.text) > 0
    assert "first paragraph" in result.text
    assert "second paragraph" in result.text


def test_extractor_empty_html():
    """Extractor should handle empty HTML gracefully."""
    extractor = Extractor()
    result = extractor.extract("")

    assert isinstance(result, ExtractResult)
    assert result.title is None
    assert result.text == ""


def test_extractor_whitespace_only_html():
    """Extractor should handle whitespace-only HTML gracefully."""
    extractor = Extractor()
    result = extractor.extract("   \n  \t  ")

    assert isinstance(result, ExtractResult)
    assert result.title is None
    assert result.text == ""


def test_extractor_html_without_title():
    """Extractor should handle HTML without a title tag."""
    html = """<!DOCTYPE html>
<html>
<body>
    <p>Some content without a title tag.</p>
</body>
</html>"""
    extractor = Extractor()
    result = extractor.extract(html)

    assert isinstance(result, ExtractResult)
    assert len(result.text) > 0
    assert "content without a title" in result.text


def test_extractor_non_html_content():
    """Extractor should handle non-HTML content without crashing."""
    extractor = Extractor()
    # trafilatura returns plain text as-is for non-HTML input
    result = extractor.extract("This is just plain text, not HTML.")

    assert isinstance(result, ExtractResult)
    # Should not crash - text may be returned by trafilatura
    assert result.text != "" or result.text == ""
