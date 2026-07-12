"""Simple DI container / service wiring.

Provides lazy initialization and dependency injection for all services.
"""

from __future__ import annotations

from typing import Optional

from crawler_endpoint.config import Settings
from crawler_endpoint.services.search_client import SearchClient
from crawler_endpoint.services.fetch_engine import FetchEngine
from crawler_endpoint.services.extractor import Extractor
from crawler_endpoint.services.storage import StorageLayer
from crawler_endpoint.services.logger import LoggerService


class Container:
    """Dependency injection container for service wiring."""

    def __init__(self) -> None:
        self._settings: Optional[Settings] = None
        self._search_client: Optional[SearchClient] = None
        self._fetch_engine: Optional[FetchEngine] = None
        self._extractor: Optional[Extractor] = None
        self._storage: Optional[StorageLayer] = None
        self._logger: Optional[LoggerService] = None

    @property
    def settings(self) -> Settings:
        if self._settings is None:
            self._settings = Settings()
        return self._settings

    @property
    def search_client(self) -> SearchClient:
        if self._search_client is None:
            self._search_client = SearchClient(self.settings)
        return self._search_client

    @property
    def fetch_engine(self) -> FetchEngine:
        if self._fetch_engine is None:
            self._fetch_engine = FetchEngine(self.settings)
        return self._fetch_engine

    @property
    def extractor(self) -> Extractor:
        if self._extractor is None:
            self._extractor = Extractor()
        return self._extractor

    @property
    def storage(self) -> StorageLayer:
        if self._storage is None:
            self._storage = StorageLayer(self.settings)
        return self._storage

    @property
    def logger(self) -> LoggerService:
        if self._logger is None:
            self._logger = LoggerService(self.settings)
        return self._logger