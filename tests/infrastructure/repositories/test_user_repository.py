"""Integration tests for the PostgreSQLUserRepository."""

import uuid
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.domain.entities.user import User
from src.domain.exceptions import UserNotFoundError
from src.infrastructure.database.connection import Database
from src.infrastructure.database.models import Base
from src.infrastructure.repositories.user_repository import PostgreSQLUserRepository


@pytest.fixture
def test_db_url():
    """Get the test database URL."""
    return "postgresql+asyncpg://postgres:postgres@localhost/test_semantic_engine"


@pytest_asyncio.fixture
async def db_session(test_db_url):
    """Create a test database session."""
    engine = create_async_engine(test_db_url)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def user_repository(test_db_url):
    """Create a test user repository."""
    database = Database(test_db_url)
    return PostgreSQLUserRepository(database)


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        last_login=None,
    )


@pytest.mark.asyncio
async def test_save_user(user_repository, sample_user):
    """Test saving a user to the repository."""
    # Act
    saved_user = await user_repository.save(sample_user)

    # Assert
    assert saved_user.id == sample_user.id
    assert saved_user.email == sample_user.email
    assert saved_user.hashed_password == sample_user.hashed_password


@pytest.mark.asyncio
async def test_find_by_id(user_repository, sample_user):
    """Test finding a user by ID."""
    # Arrange
    await user_repository.save(sample_user)

    # Act
    found_user = await user_repository.find_by_id(sample_user.id)

    # Assert
    assert found_user is not None
    assert found_user.id == sample_user.id
    assert found_user.email == sample_user.email


@pytest.mark.asyncio
async def test_find_by_email(user_repository, sample_user):
    """Test finding a user by email."""
    # Arrange
    await user_repository.save(sample_user)

    # Act
    found_user = await user_repository.find_by_email(sample_user.email)

    # Assert
    assert found_user is not None
    assert found_user.id == sample_user.id
    assert found_user.email == sample_user.email


@pytest.mark.asyncio
async def test_find_all(user_repository, sample_user):
    """Test finding all users."""
    # Arrange
    await user_repository.save(sample_user)

    # Create another user
    another_user = User(
        id=uuid.uuid4(),
        email="another@example.com",
        hashed_password="another_password",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        last_login=None,
    )
    await user_repository.save(another_user)

    # Act
    users = await user_repository.find_all()

    # Assert
    assert len(users) == 2
    emails = [user.email for user in users]
    assert sample_user.email in emails
    assert another_user.email in emails


@pytest.mark.asyncio
async def test_update_user(user_repository, sample_user):
    """Test updating a user."""
    # Arrange
    await user_repository.save(sample_user)

    # Create updated user with same ID
    updated_user = User(
        id=sample_user.id,
        email="updated@example.com",
        hashed_password="updated_password",
        is_active=True,
        is_admin=True,
        created_at=sample_user.created_at,
        updated_at=datetime.now(),
        last_login=datetime.now(),
    )

    # Act
    result = await user_repository.update(updated_user)

    # Assert
    assert result.email == "updated@example.com"
    assert result.hashed_password == "updated_password"
    assert result.is_admin is True
    assert result.last_login is not None

    # Verify in database
    found_user = await user_repository.find_by_id(sample_user.id)
    assert found_user.email == "updated@example.com"
    assert found_user.is_admin is True


@pytest.mark.asyncio
async def test_delete_user(user_repository, sample_user):
    """Test deleting a user."""
    # Arrange
    await user_repository.save(sample_user)

    # Act
    await user_repository.delete(sample_user.id)

    # Assert
    found_user = await user_repository.find_by_id(sample_user.id)
    assert found_user is None


@pytest.mark.asyncio
async def test_update_nonexistent_user(user_repository, sample_user):
    """Test updating a user that doesn't exist."""
    # Act & Assert
    with pytest.raises(UserNotFoundError):
        await user_repository.update(sample_user)


@pytest.mark.asyncio
async def test_delete_nonexistent_user(user_repository):
    """Test deleting a user that doesn't exist."""
    # Act & Assert
    with pytest.raises(UserNotFoundError):
        await user_repository.delete(uuid.uuid4())
