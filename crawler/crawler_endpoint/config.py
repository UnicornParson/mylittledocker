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

    model_config = {"env_prefix": "", "case_sensitive": False}