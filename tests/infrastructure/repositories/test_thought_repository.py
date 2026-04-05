"""Integration tests for the PostgreSQLThoughtRepository."""

import uuid
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.domain.entities.thought import (
    GeoLocation,
    Thought,
    ThoughtMetadata,
    WeatherData,
)
from src.domain.entities.user import User
from src.domain.exceptions import ThoughtNotFoundError
from src.infrastructure.database.connection import Database
from src.infrastructure.database.models import Base
from src.infrastructure.database.models import User as UserModel
from src.infrastructure.repositories.thought_repository import (
    PostgreSQLThoughtRepository,
)


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
async def thought_repository(test_db_url):
    """Create a test thought repository."""
    database = Database(test_db_url)
    return PostgreSQLThoughtRepository(database)


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user in the database."""
    user_id = uuid.uuid4()
    user = UserModel(
        id=user_id,
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=False,
    )
    db_session.add(user)
    await db_session.commit()
    return User(
        id=user_id,
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_thought(test_user):
    """Create a sample thought for testing."""
    metadata = ThoughtMetadata(
        location=GeoLocation(
            latitude=37.7749,
            longitude=-122.4194,
            name="San Francisco",
        ),
        weather=WeatherData(
            temperature=22.5,
            condition="Sunny",
            humidity=65.0,
        ),
        mood="Happy",
        tags=["work", "idea"],
        custom={"priority": "high"},
    )

    return Thought(
        id=uuid.uuid4(),
        user_id=test_user.id,
        content="This is a test thought",
        timestamp=datetime.now(),
        metadata=metadata,
        semantic_entries=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.mark.asyncio
async def test_save_thought(thought_repository, sample_thought):
    """Test saving a thought to the repository."""
    # Act
    saved_thought = await thought_repository.save(sample_thought)

    # Assert
    assert saved_thought.id == sample_thought.id
    assert saved_thought.content == sample_thought.content
    assert saved_thought.user_id == sample_thought.user_id
    assert saved_thought.metadata.location.name == "San Francisco"
    assert saved_thought.metadata.weather.condition == "Sunny"
    assert saved_thought.metadata.mood == "Happy"
    assert "work" in saved_thought.metadata.tags
    assert saved_thought.metadata.custom["priority"] == "high"


@pytest.mark.asyncio
async def test_find_by_id(thought_repository, sample_thought):
    """Test finding a thought by ID."""
    # Arrange
    await thought_repository.save(sample_thought)

    # Act
    found_thought = await thought_repository.find_by_id(sample_thought.id)

    # Assert
    assert found_thought is not None
    assert found_thought.id == sample_thought.id
    assert found_thought.content == sample_thought.content
    assert found_thought.metadata.location.name == "San Francisco"


@pytest.mark.asyncio
async def test_find_by_user(thought_repository, sample_thought, test_user):
    """Test finding thoughts by user ID."""
    # Arrange
    await thought_repository.save(sample_thought)

    # Create another thought for the same user
    another_thought = Thought(
        id=uuid.uuid4(),
        user_id=test_user.id,
        content="Another test thought",
        timestamp=datetime.now(),
        metadata=ThoughtMetadata(),
        semantic_entries=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    await thought_repository.save(another_thought)

    # Act
    thoughts = await thought_repository.find_by_user(test_user.id)

    # Assert
    assert len(thoughts) == 2
    contents = [thought.content for thought in thoughts]
    assert sample_thought.content in contents
    assert another_thought.content in contents


@pytest.mark.asyncio
async def test_update_thought(thought_repository, sample_thought):
    """Test updating a thought."""
    # Arrange
    await thought_repository.save(sample_thought)

    # Create updated thought with same ID
    updated_thought = Thought(
        id=sample_thought.id,
        user_id=sample_thought.user_id,
        content="Updated content",
        timestamp=sample_thought.timestamp,
        metadata=ThoughtMetadata(
            mood="Focused",
            tags=["updated"],
        ),
        semantic_entries=[],
        created_at=sample_thought.created_at,
        updated_at=datetime.now(),
    )

    # Act
    result = await thought_repository.update(updated_thought)

    # Assert
    assert result.content == "Updated content"
    assert result.metadata.mood == "Focused"
    assert "updated" in result.metadata.tags

    # Verify in database
    found_thought = await thought_repository.find_by_id(sample_thought.id)
    assert found_thought.content == "Updated content"
    assert found_thought.metadata.mood == "Focused"


@pytest.mark.asyncio
async def test_delete_thought(thought_repository, sample_thought):
    """Test deleting a thought."""
    # Arrange
    await thought_repository.save(sample_thought)

    # Act
    await thought_repository.delete(sample_thought.id)

    # Assert
    found_thought = await thought_repository.find_by_id(sample_thought.id)
    assert found_thought is None


@pytest.mark.asyncio
async def test_update_nonexistent_thought(thought_repository, sample_thought):
    """Test updating a thought that doesn't exist."""
    # Act & Assert
    with pytest.raises(ThoughtNotFoundError):
        await thought_repository.update(sample_thought)


@pytest.mark.asyncio
async def test_delete_nonexistent_thought(thought_repository):
    """Test deleting a thought that doesn't exist."""
    # Act & Assert
    with pytest.raises(ThoughtNotFoundError):
        await thought_repository.delete(uuid.uuid4())
