"""Database connection management for the Personal Semantic Engine."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class Database:
    """Database connection manager."""

    def __init__(self, connection_string: str):
        """Initialize the database connection.

        Args:
            connection_string: SQLAlchemy connection string for the database
        """
        self._engine = create_async_engine(
            connection_string,
            echo=False,
            pool_pre_ping=True,
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session.

        Yields:
            AsyncSession: An async SQLAlchemy session

        Example:
            ```python
            async with db.session() as session:
                result = await session.execute(query)
                await session.commit()
            ```
        """
        session = self._session_factory()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
