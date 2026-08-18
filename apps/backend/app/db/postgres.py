# apps/backend/app/db/postgres.py
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

logger = logging.getLogger(__name__)

# Async engine for PostgreSQL with improved connection pool management
engine = create_async_engine(
    settings.POSTGRES_URL,
    echo=settings.APP_DEBUG,
    future=True,
    pool_size=20,  # Increased pool size for concurrent operations
    max_overflow=40,  # Allow overflow for peak loads
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
    connect_args={
        "server_settings": {"application_name": "lumenly_backend"},
    },
)

# Async session maker with proper isolation level
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_postgres_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function that yields an async PostgreSQL session.
    Use this in FastAPI endpoints with Depends(get_postgres_session).
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_postgres() -> None:
    """Close the PostgreSQL engine connection pool on application shutdown."""
    await engine.dispose()
    logger.info("PostgreSQL connection pool closed.")
