"""
ClipForge AI — Application Configuration

Loads environment variables and provides typed settings
for the entire backend application.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        app_name: Display name for the application.
        debug: Enable debug mode (verbose logging, reloads).
        api_version: API version prefix for routes.

        llm_api_key: API key for the LLM provider (OpenRouter).
        llm_model: Model identifier for LLM calls.
        llm_base_url: Base URL for the LLM API.
        llm_max_retries: Maximum retries for LLM API calls.

        database_url: PostgreSQL connection string.
        redis_url: Redis connection string.

        max_validation_retries: Maximum clip validation retry attempts.
        clip_min_duration: Minimum clip duration in seconds.
        clip_max_duration: Maximum clip duration in seconds.
        top_clips_count: Number of top clips to return per run.

        cors_origins: Allowed CORS origins for the frontend.
    """

    # Application
    app_name: str = "ClipForge AI"
    debug: bool = False
    api_version: str = "v1"

    # LLM Provider (OpenRouter)
    llm_api_key: str = ""
    llm_model: str = "google/gemini-2.5-flash"
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_max_retries: int = 3

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/clipforge"
    redis_url: str = "redis://localhost:6379/0"

    # Pipeline Configuration
    max_validation_retries: int = 3
    clip_min_duration: int = 40
    clip_max_duration: int = 60
    top_clips_count: int = 3

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance. Call this instead of constructing Settings directly."""
    return Settings()
