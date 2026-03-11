"""
ClipForge AI — FastAPI Dependency Injection

Provides shared dependencies (database, Redis, LLM client)
injected into route handlers via FastAPI's Depends() system.
"""

from app.config import get_settings, Settings


def get_app_settings() -> Settings:
    """Dependency: returns the application settings instance."""
    return get_settings()


async def get_db():
    """Dependency: returns a database session.

    TODO: Implement with SQLAlchemy async session.
    Currently returns None as a placeholder.
    """
    # Future implementation:
    # async with AsyncSessionLocal() as session:
    #     yield session
    yield None


async def get_redis():
    """Dependency: returns a Redis client connection.

    TODO: Implement with redis-py async client.
    Currently returns None as a placeholder.
    """
    # Future implementation:
    # redis_client = await aioredis.from_url(settings.redis_url)
    # yield redis_client
    # await redis_client.close()
    yield None


def get_llm_client():
    """Dependency: returns an LLM client instance.

    TODO: Implement with LangChain ChatOpenAI pointed at OpenRouter.
    Currently returns None as a placeholder.
    """
    # Future implementation:
    # settings = get_settings()
    # from langchain_openai import ChatOpenAI
    # return ChatOpenAI(
    #     model=settings.llm_model,
    #     openai_api_key=settings.llm_api_key,
    #     openai_api_base=settings.llm_base_url,
    # )
    return None
