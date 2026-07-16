#!/bin/bash
# entrypoint.sh — запускает Flask API (gunicorn) и FastMCP (SSE + StreamableHTTP) в одном контейнере
#
# Flask API:       порт 8000 (HTTP REST)
# FastMCP SSE:     порт 8001 (Streaming HTTP для MCP-клиентов, endpoint /mcp)
# FastMCP Stream:  порт 8002 (StreamableHTTP для MCP-клиентов)

set -e

echo "[entrypoint] Starting Flask API (gunicorn) on port 8000 ..."
gunicorn \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-4}" \
    --access-logfile - \
    --error-logfile - \
    crawler_endpoint.__main__:app &

echo "[entrypoint] Starting FastMCP SSE (uvicorn) on port 8001..."
uvicorn \
    --host 0.0.0.0 \
    --port 8001 \
    --log-level "${LOG_LEVEL:-info}" \
    --proxy-headers \
    crawler_endpoint.run_mcp:mcp_app &

echo "[entrypoint] Starting FastMCP StreamableHTTP (uvicorn) on port 8101..."
uvicorn \
    --host 0.0.0.0 \
    --port 8101 \
    --log-level "${LOG_LEVEL:-info}" \
    --proxy-headers \
    crawler_endpoint.routes.fastmcp:appf &

# Wait for any child process to exit
trap 'kill $(jobs -p) 2>/dev/null; exit 0' SIGTERM SIGINT
wait