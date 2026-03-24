from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os

# SQLite database file path (Fallback)
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DB_DIR, exist_ok=True)
DEFAULT_DB_URL = f"sqlite+aiosqlite:///{os.path.join(DB_DIR, 'clipforge.db')}"

# Fetch from environment, or default to local SQLite
raw_db_url = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

# Format Postgres URLs to use the async driver (asyncpg)
if raw_db_url.startswith("postgres://"):
    DATABASE_URL = raw_db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif raw_db_url.startswith("postgresql://") and "asyncpg" not in raw_db_url:
    DATABASE_URL = raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    DATABASE_URL = raw_db_url

# Create the async engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Create an async session maker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)

Base = declarative_base()

async def get_db():
    """Dependency for injecting the database session."""
    async with AsyncSessionLocal() as session:
        yield session
