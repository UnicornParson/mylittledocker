"""Flask app factory (create_app).

Creates and configures the Flask application with:
- REST API blueprint (/api/*)
- Service layer wiring via DI container

FastMCP server runs separately via ``mcp.run(transport="sse")`` —
see ``run_mcp.py`` for the MCP entrypoint.
"""

from flask import Flask

from crawler_endpoint.routes.api import api_bp
from crawler_endpoint.di import Container


def create_app() -> Flask:
    """Create and return a configured Flask application instance."""
    app = Flask(__name__)

    # Load configuration from environment
    app.config.from_object("crawler_endpoint.config.Settings")

    # Initialize DI container
    container = Container()
    app.extensions["container"] = container

    # Register blueprints
    app.register_blueprint(api_bp, url_prefix="/api")

    return app