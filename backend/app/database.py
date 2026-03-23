from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os

# SQLite database file path
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DB_DIR, exist_ok=True)
DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(DB_DIR, 'clipforge.db')}"

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
