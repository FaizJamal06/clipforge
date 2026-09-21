"""
ClipForge AI — Application Configuration

Loads environment variables and provides typed settings
for the entire backend application.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        app_name: Display name for the application.
        debug: Enable debug mode (verbose logging, reloads).
        api_version: API version prefix for routes.

        llm_api_key: Google AI Studio API key, used directly by ChatGoogleGenerativeAI
            (see app/dependencies.py::get_llm_client). There is no provider abstraction —
            this app only ever calls Google Gemini.
        llm_model: Gemini model identifier for LLM calls (native ID, e.g. "gemini-2.5-flash").
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

    # LLM Provider — Google Gemini, called directly via langchain-google-genai.
    # (There is no OpenRouter/OpenAI-compatible layer despite the naming; see
    # app/dependencies.py::get_llm_client, which only ever constructs ChatGoogleGenerativeAI.)
    llm_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"
    llm_max_retries: int = 3

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/clipforge"
    redis_url: str = "redis://localhost:6379/0"

    # Pipeline Configuration
    max_validation_retries: int = 3
    clip_min_duration: int = 40
    clip_max_duration: int = 60
    top_clips_count: int = 3

    # LLM Rate Limiting (Gemini free tier: 5 req/min — use 4 for safety)
    llm_rate_limit_rpm: int = 4           # Max LLM requests per minute
    llm_batch_size: int = 7               # Chunks per discovery batch

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "https://clipforge.vercel.app",
        "https://clipforge-eosin.vercel.app",
        "https://*.vercel.app",
    ]

    # YouTube Settings
    youtube_api_key: str | None = Field(default=None, description="YouTube Data API v3 Key")
    youtube_proxy: str | None = Field(default=None, description="Proxy URL for fetching transcripts (e.g., http://user:pass@proxy.com:8080)")
    supadata_api_key: str | None = Field(default=None, description="Supadata API Key for fetching transcripts reliably")

    # Security
    api_keys: list[str] = []              # Allowed API keys (empty = auth disabled)
    rate_limit_per_minute: int = 20       # Max requests per IP per minute
    rate_limit_burst: int = 5             # Max burst requests in 2-second window

    # User auth — shared HS256 secret with the frontend's Auth.js config
    # (must be the exact same value as the frontend's AUTH_SECRET env var).
    # Used to verify the JWT the frontend mints after a Google sign-in.
    auth_secret: str = ""

    # Billing (Stripe, test mode is fine for a portfolio demo)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""             # a one-time Price created in the Stripe dashboard
    frontend_url: str = "http://localhost:3000"  # where Stripe sends users back to
    pro_emails: list[str] = []            # accounts that get Pro without paying (e.g. the owner)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance. Call this instead of constructing Settings directly."""
    return Settings()
