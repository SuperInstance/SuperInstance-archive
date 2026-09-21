"""
Database configuration and session management.

Provides async database session management and connection utilities.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.logging import get_logger

logger = get_logger(__name__)

# Database engine and session maker will be initialized on app startup
engine = None
SessionLocal = None


async def init_db(database_url: str) -> None:
    """
    Initialize database engine and session maker.

    Args:
        database_url: PostgreSQL connection URL
    """
    global engine, SessionLocal

    try:
        engine = create_async_engine(
            database_url,
            echo=False,  # Set to True for SQL logging
            pool_pre_ping=True,
            pool_recycle=300,
            poolclass=NullPool,  # Disable connection pooling for now
        )

        SessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False,
        )

        logger.info("Database initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise


async def close_db() -> None:
    """Close database engine and cleanup resources."""
    global engine

    if engine:
        await engine.dispose()
        logger.info("Database connection closed")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for dependency injection.

    Yields:
        AsyncSession: Database session
    """
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with SessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {str(e)}")
            await session.rollback()
            raise
        finally:
            await session.close()


# Import base class after engine configuration
from app.db.base_class import Base