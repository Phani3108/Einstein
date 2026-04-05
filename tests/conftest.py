"""Test fixtures for the Personal Semantic Engine."""

import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.api.app import create_app
from src.container import Container
from src.infrastructure.database.models import Base

# Create a test database URL
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/faraday_test",
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Create a test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def test_container() -> Container:
    """Create a test dependency injection container."""
    container = Container()
    container.config.from_dict(
        {
            "db": {
                "connection_string": TEST_DATABASE_URL,
            },
            "security": {
                "secret_key": "test-secret-key",
                "algorithm": "HS256",
                "access_token_expire_minutes": 30,
            },
            "openai": {
                "api_key": "test-api-key",
                "model": "gpt-4",
            },
            "pinecone": {
                "api_key": "test-api-key",
                "environment": "test",
                "index_name": "faraday-test",
            },
        }
    )
    return container


@pytest.fixture
def test_app(test_container) -> FastAPI:
    """Create a test FastAPI application."""
    app = create_app()
    app.container = test_container
    return app


@pytest.fixture
def test_client(test_app) -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(test_app)
