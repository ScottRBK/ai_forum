from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from sqlalchemy import text
from contextlib import asynccontextmanager
from typing import AsyncIterator

from app.repositories.postgres.postgres_tables import Base
from app.config.settings import settings

import logging
logger = logging.getLogger(__name__)


class PostgresDatabaseAdapter:
    """Database adapter for PostgreSQL with async support"""

    def __init__(self):
        self._engine: AsyncEngine = create_async_engine(
            url=self.construct_postgres_connection_string(),
            echo=settings.DB_LOGGING,
            future=True,
            pool_pre_ping=True,  # Test connections before use
            pool_size=10,  # Connection pool size
            max_overflow=20  # Extra connections if pool exhausted
        )

        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,  # Don't expire objects after commit
            autoflush=False  # Manual flush control
        )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Create a database session"""
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.exception(
                msg="Database session failed",
                extra={"error": str(e)}
            )
            await session.rollback()
            raise
        finally:
            await session.close()

    async def init_db(self) -> None:
        """Initialize database - supports both fresh and existing databases.

        - Fresh database: Creates all tables
        - Existing database: Could run Alembic migrations (not implemented yet)
        """
        async with self._engine.begin() as conn:
            logger.info("Initializing database")

            # Check if alembic_version table exists
            result = await conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version')"
            ))

            if not result.scalar():
                # Fresh database
                logger.info("Fresh database detected - creating schema")

                await conn.run_sync(Base.metadata.create_all)

                logger.info("Database schema created successfully")
                logger.warning("Alembic version not set - alembic migrations not implemented yet")
            else:
                # Existing database
                logger.info("Existing database detected")
                logger.warning("Alembic migration not applied, alembic migrations not implemented yet")

    async def dispose(self) -> None:
        """Dispose of database engine and close all connections"""
        await self._engine.dispose()

    def construct_postgres_connection_string(self) -> str:
        """Get PostgreSQL connection string from settings"""
        return settings.DATABASE_URL
