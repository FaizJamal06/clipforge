"""
ClipForge AI — FastAPI Dependency Injection

Provides shared dependencies (database, Redis, LLM client)
injected into route handlers via FastAPI's Depends() system.
"""

import logging
from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import get_settings, Settings

logger = logging.getLogger(__name__)


def get_app_settings() -> Settings:
    """Dependency: returns the application settings instance."""
    return get_settings()


async def get_db():
    """Dependency: returns a database session.

    TODO: Implement with SQLAlchemy async session in Phase 3.
    Currently returns None as a placeholder.
    """
    yield None


async def get_redis():
    """Dependency: returns a Redis client connection.

    TODO: Implement with redis-py async client in Phase 3.
    Currently returns None — transcript caching will be skipped gracefully.
    """
    yield None


@lru_cache()
def get_llm_client() -> ChatOpenAI:
    """Returns a LangChain ChatOpenAI instance pointed at OpenRouter.

    The client is cached so the same instance is reused across requests.
    Uses settings from .env for model, API key, and base URL.

    Returns:
        ChatOpenAI instance configured for OpenRouter.

    Raises:
        ValueError: If LLM_API_KEY is not set.
    """
    settings = get_settings()

    if not settings.llm_api_key:
        raise ValueError(
            "LLM_API_KEY is not set. Please add your OpenRouter API key to .env. "
            "Get one at https://openrouter.ai/keys"
        )

    llm = ChatOpenAI(
        model=settings.llm_model,
        openai_api_key=settings.llm_api_key,
        openai_api_base=settings.llm_base_url,
        max_retries=settings.llm_max_retries,
        temperature=0.3,  # Low temperature for consistent, focused outputs
    )

    logger.info(f"LLM client initialized: model={settings.llm_model}")
    return llm
