"""Entrypoint for the MCP server with SSE transport (Anthropic MCP SDK).

Runs as a standalone uvicorn ASGI server on a dedicated port.

Usage::

    # Direct python invocation
    python -m crawler_endpoint.run_mcp

    # Or via uvicorn (used in Docker entrypoint)
    uvicorn crawler_endpoint.run_mcp:mcp_app --host 0.0.0.0 --port 8001 --log-level info
"""

import os
import logging

# Configure uvicorn access log for MCP server
logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

from crawler_endpoint.routes.mcp import mcp_app

if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8001"))

    uvicorn.run(
        "crawler_endpoint.run_mcp:mcp_app",
        host=host,
        port=port,
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
    )