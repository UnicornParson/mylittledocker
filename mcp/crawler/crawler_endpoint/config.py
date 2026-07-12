"""Configuration via pydantic-settings.

Loads environment variables into a typed settings object.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    searxng_url: str = "http://searxng:8080"
    data_path: str = "/data"
    log_path: str = "/data/access.log"
    max_concurrency: int = 10
    fetch_timeout: int = 15
    fetch_retries: int = 2
    playwright_enabled: bool = False
    log_level: str = "INFO"
    port: int = 8000
    gunicorn_workers: int = 4

    # Optional SOCKS5 proxy (e.g. socks5://127.0.0.1:9050)
    # If set, ALL fetches will go through this proxy only.
    socks5_proxy: str | None = None

    model_config = {"env_prefix": "", "case_sensitive": False}