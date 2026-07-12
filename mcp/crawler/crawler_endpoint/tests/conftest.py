"""Pytest fixtures for crawler_endpoint tests."""

from typing import Generator

import pytest
from flask import Flask

from crawler_endpoint.app import create_app


@pytest.fixture
def app() -> Generator[Flask, None, None]:
    """Create a Flask app instance for testing."""
    application = create_app()
    yield application


@pytest.fixture
def client(app: Flask):
    """Create a test client for the Flask app."""
    return app.test_client()