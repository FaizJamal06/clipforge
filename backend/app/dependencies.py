"""
ClipForge AI — FastAPI Dependency Injection

Provides shared dependencies (database, Redis, LLM client)
injected into route handlers via FastAPI's Depends() system.
"""

import logging
from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

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
def get_llm_client() -> BaseChatModel:
    """Returns a LangChain ChatGoogleGenerativeAI instance pointed at Google AI Studio.

    The client is cached so the same instance is reused across requests.
    Uses settings from .env for model and API key.

    Returns:
        ChatGoogleGenerativeAI instance.

    Raises:
        ValueError: If LLM_API_KEY is not set.
    """
    settings = get_settings()

    if not settings.llm_api_key:
        raise ValueError(
            "LLM_API_KEY is not set. Please add your Google AI Studio API key to .env."
        )

    llm = ChatGoogleGenerativeAI(
        model=settings.llm_model,
        google_api_key=settings.llm_api_key,
        max_retries=settings.llm_max_retries,
        temperature=0.3,  # Low temperature for consistent, focused outputs
        max_output_tokens=4000,
    )

    logger.info(f"LLM client initialized: model={settings.llm_model}")
    return llm
