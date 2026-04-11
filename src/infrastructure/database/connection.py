"""Database connection management for the Personal Semantic Engine."""

import os
import ssl
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _is_sqlite(url: str) -> bool:
    return "sqlite" in url.lower()


class Database:
    """Database connection manager supporting PostgreSQL and SQLite."""

    def __init__(self, connection_string: str):
        connect_args: dict = {}
        engine_kwargs: dict = {
            "echo": False,
        }

        if _is_sqlite(connection_string):
            connect_args["check_same_thread"] = False
        else:
            engine_kwargs["pool_pre_ping"] = True
            if os.getenv("DATABASE_URL") and "localhost" not in connection_string:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                connect_args["ssl"] = ctx

        self._engine = create_async_engine(
            connection_string,
            connect_args=connect_args,
            **engine_kwargs,
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )
        self.is_sqlite = _is_sqlite(connection_string)

    @property
    def engine(self):
        return self._engine

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        session = self._session_factory()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
