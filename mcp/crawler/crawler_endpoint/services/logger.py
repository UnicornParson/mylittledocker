"""Structured logging service.

Writes JSON-line log entries to the configured log path.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from crawler_endpoint.config import Settings


class LoggerService:
    """Structured logger that writes JSON lines to a log file."""

    def __init__(self, settings: Settings) -> None:
        self._log_path = settings.log_path
        self._logger = logging.getLogger("crawler_endpoint")
        self._logger.setLevel(settings.log_level.upper())

        # File handler for JSON-structured logging
        handler = logging.FileHandler(self._log_path)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self._logger.addHandler(handler)

    def log(
        self,
        event: str,
        request_id: Optional[str] = None,
        query: Optional[str] = None,
        url: Optional[str] = None,
        latency_ms: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        """Write a structured JSON log entry."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "request_id": request_id,
            "query": query,
            "url": url,
            "latency_ms": latency_ms,
            "error": error,
        }
        self._logger.info(json.dumps(entry, ensure_ascii=False))

    def log_search(
        self,
        query: str,
        total_results: int,
        latency_ms: int,
        request_id: Optional[str] = None,
    ) -> None:
        """Log a search event."""
        self.log(
            event="search",
            request_id=request_id,
            query=query,
            latency_ms=latency_ms,
            error=None,
        )

    def log_fetch(
        self,
        url: str,
        status: str,
        fetch_time_ms: int,
        text_bytes: int = 0,
        request_id: Optional[str] = None,
    ) -> None:
        """Log a fetch event with status and size."""
        self.log(
            event="fetch",
            request_id=request_id,
            url=url,
            latency_ms=fetch_time_ms,
            error=status if status != "success" else None,
        )

    def log_error(
        self,
        message: str,
        request_id: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        """Log an error event."""
        self.log(
            event="error",
            request_id=request_id,
            url=url,
            error=message,
        )
